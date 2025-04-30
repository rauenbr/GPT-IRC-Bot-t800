# Use a imagem oficial do Python 3.10 como base
FROM python:3.10-slim-buster

# Diretório de trabalho
WORKDIR /app

# Copia todo o conteúdo para /app
COPY . /app

# Instala dependências
RUN pip install --no-cache-dir -r requirements.txt

# Define comando de inicialização
CMD ["python3", "-u", "chat.py"]
