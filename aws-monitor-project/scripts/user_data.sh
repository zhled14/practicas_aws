#!/bin/bash
# user-data para el Launch Template del Auto Scaling Group.
# Se ejecuta automáticamente cuando EC2 arranca la instancia.
# Instala Docker, descarga el proyecto y corre el contenedor.
#
# NOTA: reemplaza <TU_REPO_GIT> por la URL de tu repositorio (GitHub) donde
# subiste esta carpeta, y <NOMBRE_BUCKET> por el bucket de S3 que creaste.

set -e
exec > /var/log/user-data.log 2>&1

yum update -y || apt-get update -y
if command -v yum &> /dev/null; then
  amazon-linux-extras install docker -y || yum install -y docker
  service docker start
  systemctl enable docker
  yum install -y git
else
  apt-get install -y docker.io git
  systemctl start docker
  systemctl enable docker
fi

usermod -aG docker ec2-user || true

cd /home/ec2-user || cd /root
git clone <TU_REPO_GIT> app
cd app/aws-monitor-project

docker build -t infra-monitor .
docker run -d --restart unless-stopped \
  -p 80:8080 \
  -e S3_BUCKET=<NOMBRE_BUCKET> \
  -e AWS_REGION=us-east-1 \
  --name infra-monitor \
  infra-monitor
