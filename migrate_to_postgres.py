import os
import subprocess
import sys

def run_command(cmd):
    print(f"Executing: {cmd}")
    process = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    stdout, stderr = process.communicate()
    if process.returncode != 0:
        print(f"Error: {stderr.decode()}")
        return False
    return True

def migrate():
    print("🚀 Yuksar ERP SQLite -> PostgreSQL Migration Started")
    
    # 1. Dump data from SQLite
    # We exclude contenttypes and permissions to avoid integrity errors on the new DB
    dump_cmd = "python3 manage.py dumpdata --natural-foreign --natural-primary -e contenttypes -e auth.Permission --indent 2 > data_migration.json"
    if not run_command(dump_cmd):
        print("❌ Failed to dump data from SQLite.")
        return

    print("✅ Data dumped to data_migration.json")
    print("\n⚠️  STEP 2: Configure DATABASE_URL to your PostgreSQL in .env")
    print("⚠️  STEP 3: Run 'python3 manage.py migrate' on the empty Postgres DB")
    print("⚠️  STEP 4: Run 'python3 manage.py loaddata data_migration.json'")
    
    print("\n💡 NOTE: If you are using Docker, you can run these commands inside the backend container:")
    print("docker-compose exec backend python manage.py migrate")
    print("docker-compose exec backend python manage.py loaddata data_migration.json")

if __name__ == "__main__":
    migrate()
