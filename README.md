## Overview
This project is related to the contruction of a data pipeline that connects a PostgreSQL data source, Python script for data cleaning, data validation using Great Expectations, Elasticsearch, and Kibana, all orchestrated and scheduled using Apache Airflow.

- Check the file `dags\url_dataset.txt`, download the dataset and put it inside `dags` folder.
- Run `docker-compose -f airflow_ES.yaml` on console to activate the pipeline.
- Address List:
   - `localhost:8080` for **Airflow**
   - `localhost:9200` for **ElasticSearch**
   - `localhost:5601` for **Kibana**
