FROM python:3.10-slim

# MAFFT is a native aligner that pip cannot install; get it from the OS repos so
# it is on the global PATH and `mirscope strict` works with no extra setup.
RUN apt-get update \
    && apt-get install -y --no-install-recommends mafft \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY . /app

# Installs mirscope + its Python dependencies and registers the `mirscope` command.
RUN pip install --no-cache-dir .

ENTRYPOINT ["mirscope"]
CMD ["--help"]
