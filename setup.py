from setuptools import setup, find_packages

setup(
    name="dynamic_graph_rag",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "neo4j",
        "influxdb-client",
        "requests",
        "python-dotenv",
    ],
    author="Libing",
    description="Dynamic Graph RAG system with Neo4j and InfluxDB integration",
    python_requires=">=3.8",
) 