#!/bin/bash
set -e
cd ~ || exit

echo "Setting Up Bench..."

pip install frappe-bench
bench -v init frappe-bench --skip-assets --python "$(which python)"
cd ./frappe-bench || exit

bench -v setup requirements

echo "Setting Up Builder App..."
bench get-app builder "${GITHUB_WORKSPACE}"

echo "Setting Up Sites & Database..."

mkdir ~/frappe-bench/sites/builder.test
cp "${GITHUB_WORKSPACE}/.github/helper/site_config.json" ~/frappe-bench/sites/builder.test/site_config.json

mariadb --host 127.0.0.1 --port 3306 -u root -p123 -e "SET GLOBAL character_set_server = 'utf8mb4'";
mariadb --host 127.0.0.1 --port 3306 -u root -p123 -e "SET GLOBAL collation_server = 'utf8mb4_unicode_ci'";

mariadb --host 127.0.0.1 --port 3306 -u root -p123 -e "CREATE DATABASE test_builder";
mariadb --host 127.0.0.1 --port 3306 -u root -p123 -e "CREATE USER 'test_builder'@'localhost' IDENTIFIED BY 'test_builder'";
mariadb --host 127.0.0.1 --port 3306 -u root -p123 -e "GRANT ALL PRIVILEGES ON \`test_builder\`.* TO 'test_builder'@'localhost'";

mariadb --host 127.0.0.1 --port 3306 -u root -p123 -e "FLUSH PRIVILEGES";


echo "Setting Up Procfile..."

sed -i 's/^watch:/# watch:/g' Procfile
sed -i 's/^schedule:/# schedule:/g' Procfile


echo "Starting Bench..."

bench start &> bench_start.log &

CI=Yes bench build &
build_pid=$!

bench --site builder.test reinstall --yes
bench --site builder.test install-app website_builder

# wait till assets are built succesfully
wait $build_pid
