#!/usr/bin/env bash
set -e

echo "Starting MongoDB"
sudo mongod --fork --logpath /opt/edx/edx-ora/logs/mongodb.log

echo "Starting RabbitMQ"
sudo /usr/sbin/rabbitmq-server