"""Baja la carpeta del mundo desde el FTP de G-Portal.

Lee la configuracion de variables de entorno (en GitHub van como secretos):
  FTP_HOST, FTP_USER, FTP_PASS     obligatorias
  FTP_PORT                         por defecto 21
  FTP_TLS                          "1" para FTPS explicito
  FTP_WORLD_DIR                    carpeta del mundo en el servidor,
                                   por defecto save/worlds_local/gportal_unzip_ppqaovp_

Uso: python arcon/fetch_ftp.py <carpeta_destino>
"""
import ftplib
import os
import sys
from datetime import datetime, timezone


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
    names = [n for n in ftp.nlst() if n not in (".", "..")]
    # Bajamos solo los archivos del guardado actual: los _main del numero mas alto
    # y todos los .chunk (cada coordenada tiene un solo archivo vigente).
    mains = [n for n in names if n.startswith("_main.")]
    if not mains:
        sys.exit(f"No hay archivos _main en {remote}: revisa FTP_WORLD_DIR.")
    latest = max(int(n.split(".")[1]) for n in mains)
    wanted = [n for n in names if n.endswith(".chunk") or n.startswith(f"_main.{latest}.")]
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
