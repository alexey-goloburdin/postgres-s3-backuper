Backup and restore PostgreSQL database with Yandex Object Storage (or any S3-compatible storage)
===

There are two Python scripts: `backup.py` and `restore.py`. The first one creates
PostgreSQL dump, zip and encrypt it, and then upload to Yandex Object
Storage (or any S3-compatible storage). The second one finds last dump in
Yandex Object Storage, download, unzip and decrypt it, and then load to
PostgreSQL database accordingly.

[YouTube video about scripts (in Russian)](https://www.youtube.com/watch?v=30TBpI4lEPI)

For both scripts you need:

* Python3.6+ version,
* installed pip packeges from `requirements.txt`,
* Yandex Object Storage / AWS credentials in `~/.aws/credentials`,
* files with public (`backup_key.pem.pub`) and private (`backup_key.pem`) keys for encrypting and decrypting dump. You can generate both with openssl:
```sh
openssl req -x509 -nodes -days 1000000 -newkey rsa:4096 -keyout backup_key.pem\
 -subj "/C=US/ST=Illinois/L=Chicago/O=IT/CN=www.example.com" \
 -out backup_key.pem.pub
 ```
* file with PostgreSQL database password `~/.pgpass` with chmod 600, including, for example:
```sh
localhost:5432:your_database:your_db_user:your_db_user_password
```
* check `check_hostname()` function in `restore.py` — it checks hostname of current server (kind of protection against drop database tables on production server).

Example of backup database (substitute your values in the variables below,
note, that here we need public key file for encrypting database):

```sh
DB_HOSTNAME=localhost \
DB_PORT=5432 \
DB_NAME=your_database  \
DB_USER=your_db_user  \
BACKUP_KEY_PUB_FILE=/home/www/.backup_key.pem.pub \
S3_BUCKET_NAME=your_s3_bucket  \
TIME_ZONE=Europe/Moscow \
python3 backup.py
```

Example of load database (note, that here we need private key file for 
decrypting database):

```sh
DB_HOSTNAME=localhost \
DB_PORT=5432 \
DB_NAME=your_database  \
DB_USER=your_db_user  \
BACKUP_KEY_PRIVATE_FILE=/home/www/.backup_key.pem \
S3_BUCKET_NAME=your_s3_bucket  \
TIME_ZONE=Europe/Moscow \
python3 restore.py
```
