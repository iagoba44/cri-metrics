"""Script de despliegue automatizado para CRI Metrics.
Soporta: local, Docker, y cloud (Heroku/Railway/Render).
"""
import os
import sys
import subprocess
import argparse

def run_cmd(cmd, desc=""):
    print(f"\n{'='*60}")
    if desc:
        print(f"  {desc}")
    print(f"  $ {cmd}")
    print('='*60)
    result = subprocess.run(cmd, shell=True)
    return result.returncode == 0

def deploy_local():
    """Despliegue local con uvicorn."""
    print("\n[LOCAL] Iniciando servidor CRI Metrics...")
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    
    # Verificar dependencias
    if not run_cmd("python -c \"import fastapi, sqlalchemy\"", "Verificando dependencias..."):
        print("Instalando dependencias...")
        run_cmd("pip install -r requirements.txt")
    
    # Iniciar servidor
    run_cmd("uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload")

def deploy_docker():
    """Despliegue con Docker Compose."""
    print("\n[DOCKER] Construyendo y desplegando con Docker...")
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    
    run_cmd("docker-compose down", "Deteniendo contenedores existentes...")
    run_cmd("docker-compose build --no-cache", "Construyendo imagen...")
    run_cmd("docker-compose up -d", "Iniciando contenedores...")
    
    print("\n" + "="*60)
    print("  CRI Metrics desplegado en Docker!")
    print("  API:     http://localhost:8000/api/v1")
    print("  Dashboard: http://localhost:8000/static/index.html")
    print("  Health:  http://localhost:8000/api/v1/health")
    print("="*60)
    
    run_cmd("docker-compose logs -f cri-api", "Mostrando logs...")

def deploy_railway():
    """Guia para desplegar en Railway."""
    print("""
[RAILWAY] Pasos para desplegar:

1. Instalar Railway CLI:
   npm install -g @railway/cli

2. Login:
   railway login

3. Inicializar proyecto:
   railway init

4. Desplegar:
   railway up

5. Obtener dominio:
   railway domain

Variables de entorno a configurar en Railway dashboard:
- DATABASE_URL (Railway PostgreSQL)
- ALERT_WEBHOOK_URL
- ALERT_THRESHOLD=65.0
""")

def deploy_render():
    """Guia para desplegar en Render."""
    print("""
[RENDER] Pasos para desplegar:

1. Crear cuenta en https://render.com

2. New Web Service -> Connect GitHub repo

3. Configurar:
   - Build Command: pip install -r requirements.txt
   - Start Command: uvicorn app.main:app --host 0.0.0.0 --port $PORT

4. Variables de entorno:
   - DATABASE_URL (Render PostgreSQL)
   - ALERT_WEBHOOK_URL
   - PYTHON_VERSION=3.11

5. Deploy!
""")

def main():
    parser = argparse.ArgumentParser(description="Despliegue CRI Metrics")
    parser.add_argument("target", choices=["local", "docker", "railway", "render"],
                       help="Target de despliegue")
    args = parser.parse_args()
    
    if args.target == "local":
        deploy_local()
    elif args.target == "docker":
        deploy_docker()
    elif args.target == "railway":
        deploy_railway()
    elif args.target == "render":
        deploy_render()
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
