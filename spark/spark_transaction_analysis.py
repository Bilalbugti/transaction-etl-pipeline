"""
spark_transaction_analysis.py

Demonstrates the transaction pipeline's data quality and analytical
logic reimplemented using Spark's distributed DataFrame API, instead
of pandas. The dataset here is small (~20K rows) for a runnable demo,
but the code is written the way it would be at real scale (5M+ daily
records, too large for a single machine's memory) - using Spark's
lazy evaluation and distributed execution model rather than loading
everything into memory on one process, as pandas does.

Run with:
    python spark_transaction_analysis.py
"""

from pyspark.sql import SparkSession
from pyspark.sql import functions as F
from pyspark.sql.window import Window

def main():
    # In production this would point to a real cluster
    # (e.g. Databricks, EMR); local[*] uses all cores on this machine
    # to simulate distributed execution locally.
    spark = (
        SparkSession.builder
        .appName("TransactionAnalysis")
        .master("local[*]")
        .getOrCreate()
    )
    spark.sparkContext.setLogLevel("WARN")

    print("=" * 60)
    print("STAGE 1: EXTRACT")
    print("=" * 60)

    # Spark reads the CSV lazily - nothing is actually loaded into
    # memory yet, just a query plan describing how to read it.
    df = (
        spark.read
        .option("header", True)
        .option("inferSchema", True)
        .csv("raw_transactions.csv")
    )
    print(f"Schema:")
    df.printSchema()

    # .count() is an "action" - this is the point Spark actually
    # executes the read across all available cores/partitions.
    raw_count = df.count()
    print(f"Raw record count: {raw_count}")

    print("\n" + "=" * 60)
    print("STAGE 2: DATA QUALITY - DEDUPLICATION")
    print("=" * 60)

    # Distributed equivalent of pandas' duplicated() check - a window
    # function partitions the data by transaction_id across the
    # cluster, ranks by timestamp, and keeps only the first occurrence.
    dedup_window = Window.partitionBy("transaction_id").orderBy("transaction_timestamp")
    df_deduped = (
        df.withColumn("row_num", F.row_number().over(dedup_window))
          .filter(F.col("row_num") == 1)
          .drop("row_num")
    )
    deduped_count = df_deduped.count()
    print(f"After deduplication: {deduped_count} ({raw_count - deduped_count} duplicates removed)")

    print("\n" + "=" * 60)
    print("STAGE 3: DATA QUALITY - VALIDITY & BUSINESS RULES")
    print("=" * 60)

    df_clean = (
        df_deduped
        .filter(F.col("account_id").isNotNull() & (F.col("account_id") != ""))
        .filter(F.col("transaction_timestamp").isNotNull())
        .filter(
            ~((F.col("transaction_type") == "DEPOSIT") & (F.col("amount") < 0))
        )
    )
    clean_count = df_clean.count()
    print(f"After validity + business rule filters: {clean_count} "
          f"({deduped_count - clean_count} records rejected)")
    print(f"Overall pass rate: {clean_count / raw_count:.1%}")

    print("\n" + "=" * 60)
    print("STAGE 4: DISTRIBUTED AGGREGATION - VOLUME BY CHANNEL")
    print("=" * 60)

    channel_summary = (
        df_clean.groupBy("channel")
        .agg(
            F.count("*").alias("transaction_count"),
            F.round(F.sum("amount"), 2).alias("total_amount"),
            F.round(F.avg("amount"), 2).alias("avg_amount"),
        )
        .orderBy(F.desc("transaction_count"))
    )
    channel_summary.show()

    print("\n" + "=" * 60)
    print("STAGE 5: WINDOW FUNCTION - TOP ACCOUNTS BY VALUE")
    print("=" * 60)

    account_totals = (
        df_clean.groupBy("account_id")
        .agg(F.round(F.sum("amount"), 2).alias("total_value"))
    )
    rank_window = Window.orderBy(F.desc("total_value"))
    top_accounts = (
        account_totals
        .withColumn("rank", F.rank().over(rank_window))
        .filter(F.col("rank") <= 10)
    )
    top_accounts.show()

    print("\n" + "=" * 60)
    print("STAGE 6: EXECUTION PLAN (demonstrates Spark's lazy evaluation)")
    print("=" * 60)
    print("Spark builds a query plan and only executes when an action "
          "(like .show() or .count()) is called - not at each transformation step:")
    channel_summary.explain()

    print("\n" + "=" * 60)
    print("STAGE 7: WRITE OUTPUT (Parquet - columnar format for big data)")
    print("=" * 60)
    df_clean.write.mode("overwrite").parquet("output/clean_transactions_parquet")
    channel_summary.write.mode("overwrite").parquet("output/channel_summary_parquet")
    print("Written to output/ as partitioned Parquet files")

    spark.stop()
    print("\nSpark session closed.")


if __name__ == "__main__":
    main()
