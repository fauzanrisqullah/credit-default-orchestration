# =================================================
# Milestone 3

# Nama  : Fauzan Risqullah
# Batch : FTDS-024-RMT

# Objective: 
# Scenario(Fiktif): Program ini dibuat menjawab permasalahan dari salah satu bank yang menginginkan sistem untuk kebutuhan profiling 
# transaksi dari nasabah yang melakukan kredit di bank tersebut. Sistem harus mampu mengambil data historis kredit dari nasabah 
# yang disimpan di dalam database PostgreSQL. Data yang telah diambil lalu dibersihkan dan dipilih kolom yang memang dapat 
# digunakan untuk melakukan profiling. 

# Data yang sudah dibersihkan harus dijadikan file .CSV dan dilakukan validasi menggunakan Great Expectations, selain itu data 
# yang sudah dibersihkan harus dimasukkan ke dalam Elasticsearch untuk keperluan visualisasi menggunakan Kibana. Visualisasi yang 
# dilakukan menggunakan Kibana harus dapat menjawab permasalahan yang ada dengan menggunakan plot atau chart tertentu.

# Dashboard ini dibuat dengan tujuan untuk membantu **Departemen Manajemen Risiko** dalam melakukan tugas terkait pelaksanaan 
# manajemen risiko terintegrasi dan mengoordinasikan pemantauan risiko strategis terkait dengan transaksi kredit dari nasabah 
# pada bank.
# =================================================

import pandas as pd
import psycopg2 as db
import datetime as dt

from elasticsearch import Elasticsearch
from airflow import DAG
from airflow.operators.bash_operator import BashOperator
from airflow.operators.python_operator import PythonOperator

def fetchFromPostgres():
    '''
    Fungsi ini digunakan untuk mengambil data data dari PostgreSQL dan akan menyimpan dataframe dari data yang telah diambil
    dari PostgreSQL ke bentuk file csv untuk selanjutkan dilakukan pembersihan.
 
    Contoh penggunaan: 
    fetchFromPostgres() //memanggil langsung function
    '''

    conn_string=f"dbname='milestone3' host='postgres' user='airflow' password='airflow'"
    conn=db.connect(conn_string)

    df=pd.read_sql(f"select * from public.table_m3", conn)

    df.to_csv('/opt/airflow/dags/P2M3_fauzan_risqullah_data_from_postgres.csv')

def cleanData():
    '''
    Fungsi ini digunakan untuk membersihkan data PostgreSQL yang sudah diambil dan disimpan kedalam bentuk csv. Fungsi ini akan
    menyimpan dataframe yang datanya sudah dibersihkan dan disimpan kedalam bentuk csv dengan data yang sudah bersih.
        
    Contoh penggunaan:
    cleanData() //memanggil langsung function
    '''

    df = pd.read_csv('/opt/airflow/dags/P2M3_fauzan_risqullah_data_from_postgres.csv')

    #Drop duplicated value
    df = df.drop_duplicates(keep='last')

    #Select only certain columns
    # Dengan asumsi dan domain knowledge yang ada, setelah melalui proses ekplorasi awal terhadap dataset, diputuskan untuk menggunakan
    # kolom - kolom yang memang relevan saja dengan permasalahan yang utama, yakni mengenai pemahaman resiko kredit nasabah berdasarkan
    # histori transaksi dan data pribadi lainnya. Ini dilakukan karena salah satu file pada dataset berisi mengenai fungsi dari 
    # masing - masing kolom dan diputuskan bahwa tidak semua kolom relevan dengan problem yang ada, misalnya luas tempat tinggal, 
    # orang yang menemani saat nasabah meng-apply pinjaman atau kredit dan lain - lain.
    usedCols = ['SK_ID_CURR', 'TARGET', 'NAME_CONTRACT_TYPE', 'CODE_GENDER', 'FLAG_OWN_CAR', 'FLAG_OWN_REALTY', 'CNT_CHILDREN', 
                'AMT_INCOME_TOTAL','AMT_CREDIT', 'AMT_ANNUITY', 'AMT_GOODS_PRICE', 'NAME_INCOME_TYPE', 'NAME_EDUCATION_TYPE', 
                'NAME_FAMILY_STATUS', 'NAME_HOUSING_TYPE', 'OCCUPATION_TYPE', 'CNT_FAM_MEMBERS', 'WEEKDAY_APPR_PROCESS_START', 
                'HOUR_APPR_PROCESS_START', 'ORGANIZATION_TYPE', 'DAYS_LAST_PHONE_CHANGE']
    df = df[usedCols]

    #Handling missing value - Numeric
    # Handling missing value terhadap kolom numeric adalah dengan cara mengisinya dengan nilai median dari kolom masing - masing.
    # Ini dilakukan karena diketahui saat eksplorasi terhadap dataset, kolom numeric dengan nilai null ini memiliki distribusi yang
    # skew dengan jumlah yang tidak terlalu banyak. Sehingga diputuskan bahwa untuk mengisi nilai null dengan nilai mediannya.
    df['AMT_ANNUITY'] = df['AMT_ANNUITY'].fillna(df['AMT_ANNUITY'].median())
    df['AMT_GOODS_PRICE'] = df['AMT_GOODS_PRICE'].fillna(df['AMT_GOODS_PRICE'].median())
    df['CNT_FAM_MEMBERS'] = df['CNT_FAM_MEMBERS'].fillna(df['CNT_FAM_MEMBERS'].median())
    df['DAYS_LAST_PHONE_CHANGE'] = df['DAYS_LAST_PHONE_CHANGE'].fillna(df['DAYS_LAST_PHONE_CHANGE'].median())

    #Handling missing value - Categorical
    # Untuk handling missing value kolom categorical, diketahui pada saat proses eksplorasi terhadap dataset, nilai null pada kolom
    # categorical memiliki jumlah yang sangat banyak (>30%). Maka dari itu diputuskan untuk memberi label "Other" terhadap nasabah
    # dengan pekerjaan yang memiliki value null.
    df['OCCUPATION_TYPE'] = df['OCCUPATION_TYPE'].fillna('Other')

    #Fixation columns
    df['CNT_FAM_MEMBERS'] = df['CNT_FAM_MEMBERS'].astype('int64') #Jumlah family member pada dataset disimpan dalam bentuk float
    df['FLAG_OWN_CAR'] = df['FLAG_OWN_CAR'].map({'N': 0, 'Y': 1}) #Encoding menjadi bentuk binary
    df['FLAG_OWN_REALTY'] = df['FLAG_OWN_REALTY'].map({'N': 0, 'Y': 1}) #Encoding menjadi bentuk binary
    df['DAYS_LAST_PHONE_CHANGE'] = abs(df['DAYS_LAST_PHONE_CHANGE']) #Pada dataset nilai di-record dalam bentuk angka negatif

    #Converting columns name to lowercase
    df.columns = df.columns.str.lower()

    #Saving dataframe to csv file
    df.to_csv('/opt/airflow/dags/P2M3_fauzan_risqullah_data_clean.csv')
    
def insertToElasticsearch():
    '''
    Fungsi ini digunakan untuk memasukkan data dari file csv yang datanya sudah dibersihkan (cleaning) ke dalam Elasticsearch.
    
    Contoh penggunaan:
    insertToElasticsearch() //memanggil langsung function
    '''

    es = Elasticsearch(hosts='elasticsearch')
    df = pd.read_csv('/opt/airflow/dags/P2M3_fauzan_risqullah_data_clean.csv')

    for i,r in df.iterrows():
        doc=r.to_json()
        res=es.index(index="credit_risk_case",doc_type="doc",body=doc)
        print(res)

default_args = {
    'owner': 'fauzan_risqullah',
    'start_date': dt.datetime(2023, 11, 23, 21, 32, 0) - dt.timedelta(hours=7),
    'retries': 1,
    'retry_delay': dt.timedelta(minutes=1),
}
 
with DAG('fauzan_milestone3',
         default_args=default_args,
         schedule_interval='30 23 * * *', #Di set untuk DAG agar dijalankan setiap pukul 23:30 UTC atau 06:30 WIB (UTC+7).
         ) as dag:

    startMessage = BashOperator(task_id='startMessage',
                                bash_command='echo "Start fetching data from Postgres...."')
    
    fetchPostgres = PythonOperator(task_id='fetchPostgres',
                                   python_callable=fetchFromPostgres)
    
    startCleaningMessage = BashOperator(task_id='startCleaningMessage',
                                        bash_command='echo "Start cleaning data...."')
    
    dataCleaning = PythonOperator(task_id='dataCleaning',
                                  python_callable=cleanData)
    
    startInserting = BashOperator(task_id='startInserting',
                                  bash_command='echo "Start inserting to Elasticsearch...."')

    insertElastic = PythonOperator(task_id='insertElastic',
                                   python_callable=insertToElasticsearch)
    
    endMessage = BashOperator(task_id='endMessage',
                              bash_command='echo "Done inserting to Elasticsearch"')
    
startMessage >> fetchPostgres >> startCleaningMessage >> dataCleaning >> startInserting >> insertElastic >> endMessage
