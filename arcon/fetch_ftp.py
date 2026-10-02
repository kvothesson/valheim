"""Baja la carpeta del mundo desde el FTP de G-Portal.

Lee la configuracion de variables de entorno (en GitHub van como secretos):
  FTP_HOST, FTP_USER, FTP_PASS     obligatorias
  FTP_PORT                         por defecto 21
  FTP_TLS                          "1" para FTPS explicito
  FTP_WORLD_DIR                    carpeta del mundo en el servidor,
                                   por defecto save/worlds_local/gportal_unzip_ppqaovp_

A cada archivo bajado le pone la fecha que tiene en el servidor, porque de ahi
sale la hora del guardado que muestra la pagina.

Uso: python arcon/fetch_ftp.py <carpeta_destino>
"""
import ftplib
import os
import sys
from datetime import datetime, timezone

MONTHS = {m: i for i, m in enumerate(["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"], 1)}


def _utc(dt):
    return dt.replace(tzinfo=timezone.utc).timestamp()


def _from_list_line(parts):
    """Fecha de una linea estilo ls: 'Oct  2 19:26' (este anio) u 'Oct  2  2025'."""
    mon, day, hm = parts[5], int(parts[6]), parts[7]
    now = datetime.now(timezone.utc)
    if ":" in hm:
        h, m = map(int, hm.split(":"))
        dt = datetime(now.year, MONTHS[mon], day, h, m)
        if dt > now.replace(tzinfo=None):
            dt = dt.replace(year=now.year - 1)
        return _utc(dt)
    return _utc(datetime(int(hm), MONTHS[mon], day))


def list_files(ftp):
    """{nombre: fecha (epoch) o None} de la carpeta actual, y de donde salieron las fechas.

    El FTP de G-Portal no implementa NLST, asi que se prueba MLSD y despues LIST."""
    try:
        out = {}
        for name, facts in ftp.mlsd():
            if facts.get("type") == "file":
                mod = facts.get("modify")
                out[name] = _utc(datetime.strptime(mod[:14], "%Y%m%d%H%M%S")) if mod else None
        return out, "MLSD"
    except ftplib.error_perm:
        pass
    lines = []
    ftp.retrlines("LIST", lines.append)
    out = {}
    for line in lines:
        if not line or line.startswith(("d", "total")):
            continue
        parts = line.split(None, 8)
        try:
            out[parts[-1]] = _from_list_line(parts)
        except (ValueError, KeyError, IndexError):
            out[parts[-1]] = None
    return out, "LIST"


def main(dest):
    missing = [k for k in ("FTP_HOST", "FTP_USER", "FTP_PASS") if not os.environ.get(k)]
    if missing:
        sys.exit(f"Faltan los secretos {', '.join(missing)}: cargalos en Settings > Secrets and variables > Actions.")
    host, user, pw = os.environ["FTP_HOST"], os.environ["FTP_USER"], os.environ["FTP_PASS"]
    port = int(os.environ.get("FTP_PORT") or 21)
    remote = os.environ.get("FTP_WORLD_DIR") or "save/worlds_local/gportal_unzip_ppqaovp_"
    ftp = ftplib.FTP_TLS() if os.environ.get("FTP_TLS") == "1" else ftplib.FTP()
    ftp.connect(host, port, timeout=60)
    ftp.login(user, pw)
    if isinstance(ftp, ftplib.FTP_TLS):
        ftp.prot_p()
    ftp.cwd(remote)
    os.makedirs(dest, exist_ok=True)
    files, source = list_files(ftp)
    # Bajamos solo los archivos del guardado actual: los _main del numero mas alto
    # y todos los .chunk (cada coordenada tiene un solo archivo vigente).
    mains = [n for n in files if n.startswith("_main.")]
    if not mains:
        sys.exit(f"No hay archivos _main en {remote}: revisa FTP_WORLD_DIR.")
    latest = max(int(n.split(".")[1]) for n in mains)
    wanted = [n for n in files if n.endswith(".chunk") or n.startswith(f"_main.{latest}.")]
    dated = 0
    for n in wanted:
        path = os.path.join(dest, n)
        with open(path, "wb") as f:
            ftp.retrbinary(f"RETR {n}", f.write)
        t = files.get(n)
        if t is None:
            try:
                ts = ftp.voidcmd(f"MDTM {n}")[4:].strip()
                t = _utc(datetime.strptime(ts[:14], "%Y%m%d%H%M%S"))
            except (ftplib.all_errors, ValueError):
                t = None
        if t is not None:
            os.utime(path, (t, t))
            dated += 1
    ftp.quit()
    print(f"Bajados {len(wanted)} archivos del guardado {latest} desde {remote}; "
          f"fechas del servidor: {dated}/{len(wanted)} (listado con {source})")
    if not dated:
        print("::warning::El FTP no informó fechas: la hora del guardado va a ser la de la descarga.")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    main(sys.argv[1])
