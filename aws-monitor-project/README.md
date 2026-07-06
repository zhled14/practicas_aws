# Mini Plataforma de Monitoreo de Infraestructura en AWS

Proyecto de práctica para la entrevista técnica del 9 de julio (LEGO - IT Tech
Service Specialist). Integra en un solo proyecto todos los temas de la guía de
repaso: Linux, Bash, Python, Docker, Redes y AWS (IAM, EC2, ELB, ASG, S3).

## Qué es

Una app Python/Flask que:
- Muestra qué instancia EC2 respondió (para ver el balanceo de carga del ALB en vivo).
- Expone `/health` para el health check del Target Group.
- Expone `/report`: replica el análisis de TPY que hacías en Lenovo — lee un
  CSV de resultados de prueba, calcula % de éxito y top causas de falla con
  Pandas, y sube el reporte como JSON a S3 usando un rol de IAM (sin
  credenciales hardcodeadas).

## Arquitectura objetivo

```
Internet
   |
[Application Load Balancer]  (2 subnets públicas, 2 AZs)
   |
[Target Group] --health check--> /health
   |
[Auto Scaling Group] (min 2, desired 2, max 4)
   |            |
[EC2 #1]     [EC2 #2]   <- cada una corre el contenedor Docker (user_data.sh)
   |            |
   +--- rol IAM (permiso: s3:PutObject sobre 1 bucket) ---+
                |
             [S3 bucket]  <- reportes JSON
```

## Plan día a día (hoy 5 jul -> 8 jul, entrevista el 9)

**Hoy (5 jul) - desarrollo local (~2 hrs)**
1. Probar la app localmente:
   ```
   cd aws-monitor-project
   docker build -t infra-monitor .
   docker run -p 8080:8080 infra-monitor
   ```
   Abre `http://localhost:8080` y `http://localhost:8080/report`.
2. Sube esta carpeta a un repo de GitHub (público o privado) — el
   `user_data.sh` la clona desde ahí en la instancia EC2.

**Lunes 6 jul - Fundamentos AWS (~3-4 hrs)**
1. Crea un bucket S3 (nombre único, ej. `oscar-infra-monitor-reports`).
2. Crea un rol de IAM para EC2 con esta policy (mínimo privilegio, solo a tu bucket):
   ```json
   {
     "Version": "2012-10-17",
     "Statement": [{
       "Effect": "Allow",
       "Action": ["s3:PutObject"],
       "Resource": "arn:aws:s3:::NOMBRE_BUCKET/reportes/*"
     }]
   }
   ```
3. Red: usa el VPC por default o crea uno con 2 subnets públicas en 2 AZs
   distintas (el ALB lo exige). Crea 2 Security Groups:
   - `alb-sg`: permite entrada 80/443 desde 0.0.0.0/0.
   - `app-sg`: permite entrada al puerto 80 SOLO desde `alb-sg`, y SSH (22)
     solo desde tu propia IP.
4. Lanza 1 instancia EC2 (t2.micro/t3.micro, Free Tier) a mano con el rol IAM,
   el `app-sg`, y pega el contenido de `scripts/user_data.sh` (con tu repo y
   bucket reales) en "User data".
5. Verifica: entra a la IP pública de la instancia en el navegador, revisa
   `/report`, y confirma que aparece el archivo en S3.

**Martes 7 jul - Load Balancer + Auto Scaling (~2-3 hrs)**
1. Crea un Launch Template con la misma AMI, tipo de instancia, `app-sg`, rol
   IAM y el mismo `user_data.sh`.
2. Crea un Target Group (HTTP, puerto 80, health check path `/health`).
3. Crea el Application Load Balancer usando las 2 subnets públicas, el
   `alb-sg` y el Target Group.
4. Crea el Auto Scaling Group (min 2, deseado 2, max 4) usando el Launch
   Template, asociado al Target Group, en las mismas 2 subnets.
5. Prueba: entra varias veces a la URL del ALB (Ctrl+F5) y confirma que el
   Instance ID cambia entre refrescos. Termina una instancia manualmente
   desde la consola y observa cómo el ASG la reemplaza sola.

**Miércoles 8 jul - Pulido y repaso (~1-2 hrs)**
1. Toma 2-3 capturas de pantalla (consola de EC2/ASG, la página web, el
   bucket S3 con reportes) por si hay problemas de conexión el día de la
   entrevista y quieres mostrar evidencia.
2. Practica explicar el proyecto en 60-90 segundos (ver abajo).
3. Termina el ASG (Auto Scaling Group -> editar capacidad a 0 o eliminarlo) y
   el ALB si no los vas a usar más, para no generar costos innecesarios.
4. Repasa la guía de estudio técnica.

## Cómo explicarlo en la entrevista (versión corta)

> "Para practicar antes de esta entrevista construí un mini sistema de
> monitoreo: una app en Python/Flask, containerizada con Docker, desplegada
> en AWS detrás de un Application Load Balancer con un Auto Scaling Group de
> mínimo 2 instancias para alta disponibilidad. Las instancias usan un rol de
> IAM con permisos mínimos para subir reportes a S3. La app también replica
> la lógica de análisis de fallas que hacía en Lenovo: lee logs de prueba y
> calcula tasa de éxito y top causas de falla con Pandas. Configuré la red
> con security groups separados para el balanceador y las instancias, y
> probé la resiliencia terminando una instancia a mano para confirmar que el
> Auto Scaling Group la reemplazaba automáticamente."

## Costos

Con instancias t2.micro/t3.micro (Free Tier) y sin NAT Gateway, el costo es
mínimo (el ALB tiene un costo por hora, unos centavos de dólar por 2-3 días
de uso). Elimina el ALB y el ASG cuando termines de practicar.
