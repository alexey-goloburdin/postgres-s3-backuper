"""
Renew database on current server, if hostname startswith loader*
or ends with .local (can be modified in check_hostname function below).
Script download last dump from S3 (Yandex Object Storage), decrypt
and load it after clear current database state.
"""
import os
from pathlib import Path
import socket

import boto3
import psycopg2
from termcolor import colored


DB_HOSTNAME = os.getenv("DB_HOSTNAME", "localhost")
DB_NAME = os.getenv("DB_NAME")
DB_USER = os.getenv("DB_USER")
S3_BUCKET_NAME = os.getenv("S3_BUCKET_NAME")
BACKUP_KEY_PRIVATE_FILE = os.getenv("BACKUP_KEY_PRIVATE_FILE")

DB_FILENAME = '/tmp/backup_db.sql.gz.enc'

connection = psycopg2.connect(
    f"dbname={DB_NAME} user={DB_USER} host='{DB_HOSTNAME}'")
cursor = connection.cursor()


def say_hello():
    print(colored(
        "This tool will download last database backup from Yandex Object "
        "Storage,\n decompress and unzip it, and then load to local "
        "database\n",
        "cyan"))


def check_hostname():
    hostname = socket.gethostname()
    if not hostname.startswith('loader-') and not hostname.endswith('.local'):
        exit(f"\U00002757 It seems this is not loader server "
             f"({colored(hostname, 'red')}), exit.")
    print(colored("We are on some loader or local server, ok\n", "green"))


def check_key_file_exists():
    if not Path(BACKUP_KEY_PRIVATE_FILE).is_file():
        exit(
            f"""\U00002757 Private encrypt key ({BACKUP_KEY_PRIVATE_FILE}) "
            "not found. You can find help here: "
            "https://www.imagescape.com/blog/2015/12/18/encrypted-postgres-backups/"""
        )


def get_s3_instance():
    session = boto3.session.Session()
    return session.client(
        service_name='s3',
        endpoint_url='https://storage.yandexcloud.net'
    )


def get_last_backup_filename():
    s3 = get_s3_instance()
    dumps = s3.list_objects(Bucket=S3_BUCKET_NAME)['Contents']
    dumps.sort(key=lambda x: x['LastModified'])
    last_backup_filename = dumps[-1]
    print(f"\U000023F3 Last backup in S3 is {last_backup_filename['Key']}, "
          f"{round(last_backup_filename['Size'] / (1024*1024))} MB, "
          f"download it")
    return last_backup_filename['Key']


def download_s3_file(filename: str):
    _silent_remove_file(filename)
    get_s3_instance().download_file(S3_BUCKET_NAME, filename, DB_FILENAME)
    print(f"\U0001f680 Downloaded")


def unencrypt_database():
    operation_status = os.WEXITSTATUS(os.system(
        f"""openssl smime -decrypt -in {DB_FILENAME} -binary \
            -inform DEM -inkey {BACKUP_KEY_PRIVATE_FILE} \
            -out /tmp/db.sql.gz"""
    ))
    if operation_status != 0:
        exit(f"\U00002757 Can not unecrypt db file, status "
             f"{operation_status}.")
    print(f"\U0001F511 Database unecnrypted")


def unzip_database():
    _silent_remove_file("/tmp/db.sql")
    operation_status = os.WEXITSTATUS(os.system(
        f"""gzip -d /tmp/db.sql.gz"""
    ))
    if operation_status != 0:
        exit(f"\U00002757 Can not unecrypt db file, status "
             f"{operation_status}.")
    print(f"\U0001F4E4 Database unzipped")


def clear_database():
    tables = _get_all_db_tables()
    if not tables:
        return
    with connection:
        with connection.cursor() as local_cursor:
            local_cursor.execute("\n".join([
                f'drop table if exists "{table}" cascade;'
                for table in tables]))
    print(f"\U0001F633 Database cleared")


def load_database():
    print(f"\U0001F4A4 Database load started")
    operation_status = os.WEXITSTATUS(os.system(
        f"""psql -h {DB_HOSTNAME} -U {DB_USER} {DB_NAME} < /tmp/db.sql"""
    ))
    if operation_status != 0:
        exit(f"\U00002757 Can not load database, status {operation_status}.")
    print(f"\U0001F916 Database loaded")


def remove_temp_files():
    _silent_remove_file(DB_FILENAME)
    print(colored("\U0001F44D That's all!", "green"))


def _get_all_db_tables():
    cursor.execute("""SELECT table_name FROM information_schema.tables
                      WHERE table_schema = 'public' order by table_name;""")
    results = cursor.fetchall()
    tables = []
    for row in results:
        tables.append(row[0])
    return tables

def _silent_remove_file(filename: str):
    try:
        os.remove(filename)
    except FileNotFoundError:
        pass


if __name__ == "__main__":
    say_hello()
    check_hostname()
    check_key_file_exists()
    download_s3_file(get_last_backup_filename())
    unencrypt_database()
    unzip_database()
    clear_database()
    load_database()
    remove_temp_files()
