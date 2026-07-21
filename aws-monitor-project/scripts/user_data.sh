#!/bin/bash
# Utiliza esto para tus datos de usuario
# Instala httpd (Version: Linux 2)
set -xe

yum update -y

#yum install -y httpd
yum install -y docker
yum install -y git

#systemctl start httpd
systemctl start docker

#systemctl enable httpd
systemctl enable docker

until docker info >/dev/null 2>&1; do
    sleep 2
done

sudo usermod -aG docker ec2-user

cd /home/ec2-user
git clone https://github.com/zhled14/practicas_aws.git app
cd app/aws-monitor-project
export S3_BUCKET="amzn-s3-intee-prep"
docker build -t infra-monitor .
docker run -d \
  -p 80:8080 \
  --name infra-monitor-test \
  -e S3_BUCKET="$S3_BUCKET" \
  -e AWS_REGION="us-east-1" \
  infra-monitor