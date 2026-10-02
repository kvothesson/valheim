"""Baja la carpeta del mundo desde el FTP de G-Portal.

Lee la configuracion de variables de entorno (en GitHub van como secretos):
  FTP_HOST, FTP_USER, FTP_PASS     obligatorias
  FTP_PORT                         por defecto 21
  FTP_TLS                          "1" para FTPS explicito
  FTP_WORLD_DIR                    carpeta del mundo en el servidor,
                                   por defecto save/worlds_local/gportal_unzip_ppqaovp_
  PUBLISHED_SAVE                   numero del guardado ya publicado; si es el mismo
                                   que el del servidor, no baja nada y avisa skip=true

Uso: python arcon/fetch_ftp.py <carpeta_destino>
"""
import ftplib
import os
import sys
from datetime import datetime, timezone


def list_files(ftp):
    """Nombres de archivos de la carpeta actual. El FTP de G-Portal no implementa
    NLST, asi que se prueba MLSD y despues LIST (formato ls: el nombre va al final)."""
    try:
        return [n for n, facts in ftp.mlsd() if facts.get("type") == "file"]
    except ftplib.error_perm:
        pass
    lines = []
    ftp.retrlines("LIST", lines.append)
    return [l.split(None, 8)[-1] for l in lines if l and not l.startswith(("d", "total"))]


def set_output(key, value):
    """Deja un valor para los pasos siguientes del workflow (no hace nada fuera de GitHub)."""
    path = os.environ.get("GITHUB_OUTPUT")
    if path:
        with open(path, "a") as f:
            f.write(f"{key}={value}\n")


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
    names = list_files(ftp)
    # Bajamos solo los archivos del guardado actual: los _main del numero mas alto
    # y todos los .chunk (cada coordenada tiene un solo archivo vigente).
    mains = [n for n in names if n.startswith("_main.")]
    if not mains:
        sys.exit(f"No hay archivos _main en {remote}: revisa FTP_WORLD_DIR.")
    latest = max(int(n.split(".")[1]) for n in mains)
    published = os.environ.get("PUBLISHED_SAVE", "").strip()
    if published == str(latest):
        # Mismo guardado que la pagina publicada: no hay nada nuevo que mostrar.
        ftp.quit()
        print(f"El guardado {latest} ya está publicado; no se actualiza.")
        set_output("skip", "true")
        return
    set_output("skip", "false")
    wanted =[n for n in names if n.endswith(".chunk") or n.startswith(f"_main.{latest}.")]
    for n in wanted:
        path = os.path.join(dest, n)
        with open(path, "wb") as f:
            ftp.retrbinary(f"RETR {n}", f.write)
        try:
            ts = ftp.voidcmd(f"MDTM {n}")[4:].strip()
            t = datetime.strptime(ts[:14], "%Y%m%d%H%M%S").replace(tzinfo=timezone.utc).timestamp()
            os.utime(path, (t, t))
        except ftplib.all_errors:
            pass
    ftp.quit()
    print(f"Bajados {len(wanted)} archivos del guardado {latest} desde {remote}")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    main(sys.argv[1])
