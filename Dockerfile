FROM python:3.10-slim

# MAFFT is a native aligner that pip cannot install; get it from the OS repos so
# it is on the global PATH and `mirscope strict` works with no extra setup.
RUN apt-get update \
    && apt-get install -y --no-install-recommends mafft \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY . /app

# Installs mirscope + its Python dependencies (including streamlit/plotly) and
# registers the mirscope / mirscope-setup / mirscope-explore commands.
RUN pip install --no-cache-dir .

# Streamlit port for `mirscope-explore`.
EXPOSE 8501

ENTRYPOINT ["mirscope"]
CMD ["--help"]
