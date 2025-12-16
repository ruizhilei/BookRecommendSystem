# train_als.py
from pyspark.sql import SparkSession
from pyspark.sql.functions import col
from pyspark.ml.recommendation import ALS
import os

HDFS_RATINGS = "/book_recommend/data/ratings.csv"
HDFS_BOOKS = "/book_recommend/data/books.csv"
ALS_MODEL_PATH = "/book_recommend/model/als_model"
LOCAL_DATA_DIR = "data"
LOCAL_ITEM_FACTORS_CSV = os.path.join(LOCAL_DATA_DIR, "als_item_factors.csv")

def main():
    spark = SparkSession.builder \
        .appName("TrainALSBookRecommend") \
        .getOrCreate()

    # 1. 读 ratings.csv（Goodbooks 原始评分）
    ratings = spark.read.csv(
        HDFS_RATINGS,
        header=True,
        inferSchema=True
    )

    # 数据集中列名一般是：user_id, book_id, rating
    # 有的版本叫 "book_id","user_id","rating"，你可以用 printSchema() 看一下
    ratings = ratings.select(
        col("user_id").cast("int").alias("userId"),
        col("book_id").cast("int").alias("itemId"),
        col("rating").cast("float").alias("rating")
    ).na.drop()

    # 2. 训练 ALS 模型（只要 item 向量）
    als = ALS(
        userCol="userId",
        itemCol="itemId",
        ratingCol="rating",
        rank=50,
        maxIter=15,
        regParam=0.1,
        coldStartStrategy="drop",
        nonnegative=True
    )

    model = als.fit(ratings)

    # 3. 保存模型到 HDFS（以后你想用 Spark 在线推理也可以复用）
    model.write().overwrite().save(ALS_MODEL_PATH)

    # 4. 导出 itemFactors 到本地 CSV（给 Flask 用）
    # itemFactors: id, features（一个向量）
    item_factors = model.itemFactors  # id -> 向量

    # 把 features 展开成多列 f0, f1, ...
    rank = len(item_factors.first()["features"])
    cols = ["id"] + [f"f{i}" for i in range(rank)]

    from pyspark.sql.functions import udf
    from pyspark.sql.types import FloatType

    # 依次取 features[i] 到独立列
    for i in range(rank):
        item_factors = item_factors.withColumn(
            f"f{i}",
            col("features")[i].cast("float")
        )
    item_factors = item_factors.select(cols)

    # 5. 将 HDFS 的 book_id 与 item的 id 对齐
    # Goodbooks 的 book_id 就是我们训练时的 itemId，所以这里直接当作 book_id 用
    # 为了语义清晰，把 id 改名为 book_id
    item_factors = item_factors.withColumnRenamed("id", "book_id")

    # 6. 保存到本地
    if not os.path.exists(LOCAL_DATA_DIR):
        os.makedirs(LOCAL_DATA_DIR, exist_ok=True)

    item_factors.coalesce(1).write.mode("overwrite").option("header", True).csv(
        "file://" + os.path.abspath(LOCAL_ITEM_FACTORS_CSV)
    )

    # 注意：上面写 CSV 会生成一个目录，里面有 part-*.csv，你稍后手动挑一个文件重命名
    spark.stop()

if __name__ == "__main__":
    main()

