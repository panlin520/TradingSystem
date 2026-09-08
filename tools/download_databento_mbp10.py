"""
tools/download_databento_mbp10.py

============================================================
Databento MBP-10 Downloader
============================================================

职责：

    从 Databento Historical API 下载：

        CME ESU6
        MBP-10
        2026-06-15

用途：

    作为我们的 MBO L3 OrderBook 重建结果的
    官方 Ground Truth 对照数据。


============================================================

数据：

    dataset:
        GLBX.MDP3

    symbol:
        ESU6

    schema:
        mbp-10

    start:
        2026-06-15T00:00:00Z

    end:
        2026-06-16T00:00:00Z


输出：

    data/ESU6_2026-06-15_MBP10.dbn.zst


============================================================

API Key：

不要把 API Key 写进代码。

Windows PowerShell：

    $env:DATABENTO_API_KEY="db-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"


然后运行：

    python tools/download_databento_mbp10.py


============================================================
"""


from pathlib import Path
import os
import sys


try:

    import databento as db

except ImportError:

    print(
        "ERROR: databento package not installed."
    )

    print(
        "Run:"
    )

    print(
        "pip install -U databento"
    )

    sys.exit(1)



# ============================================================
# Configuration
# ============================================================


DATASET = "GLBX.MDP3"

SYMBOL = "ESU6"

SCHEMA = "mbp-10"


START = "2026-06-15T00:00:00Z"

END = "2026-06-16T00:00:00Z"



# ============================================================
# Project path
# ============================================================


PROJECT_ROOT = Path(
    __file__
).resolve().parent.parent


DATA_DIR = (
    PROJECT_ROOT
    /
    "data"
)


OUTPUT_FILE = (
    DATA_DIR
    /
    "ESU6_2026-06-15_MBP10.dbn.zst"
)



# ============================================================
# API Key
# ============================================================


def check_api_key():
    """
    检查 Databento API Key。

    Databento Python client 默认读取：

        DATABENTO_API_KEY

    环境变量。
    """


    api_key = os.environ.get(
        "DATABENTO_API_KEY"
    )


    if not api_key:

        print()

        print(
            "=" * 60
        )

        print(
            "DATABENTO API KEY NOT FOUND"
        )

        print(
            "=" * 60
        )

        print()

        print(
            "Set API key in PowerShell:"
        )

        print()

        print(
            '$env:DATABENTO_API_KEY="db-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"'
        )

        print()

        return False


    if not api_key.startswith(
        "db-"
    ):

        print(
            "WARNING:"
        )

        print(
            "DATABENTO_API_KEY does not start with 'db-'."
        )


    return True



# ============================================================
# Create client
# ============================================================


def create_client():
    """
    创建 Historical API client。

    不显式传 API Key。

    Databento 自动读取：

        DATABENTO_API_KEY
    """


    return db.Historical()



# ============================================================
# Check availability
# ============================================================


def check_dataset_range(
    client
):
    """
    查询 GLBX.MDP3 当前可访问的数据范围。

    这里只用于诊断。
    """


    print()

    print(
        "=" * 60
    )

    print(
        "CHECK DATASET RANGE"
    )

    print(
        "=" * 60
    )


    available_range = (
        client.metadata.get_dataset_range(
            dataset=DATASET
        )
    )


    print(
        "dataset:",
        DATASET
    )


    print(
        "start:",
        available_range.get(
            "start"
        )
    )


    print(
        "end:",
        available_range.get(
            "end"
        )
    )


    schema_ranges = (
        available_range.get(
            "schema",
            {}
        )
    )


    mbp10_range = (
        schema_ranges.get(
            SCHEMA
        )
    )


    print()


    if mbp10_range:

        print(
            "MBP-10 availability:"
        )

        print(
            mbp10_range
        )

    else:

        print(
            "WARNING:"
        )

        print(
            "mbp-10 availability not found "
            "in metadata response."
        )



# ============================================================
# Estimate cost
# ============================================================


def estimate_cost(
    client
):
    """
    下载前查询官方费用预估。

    不产生正式数据下载。
    """


    print()

    print(
        "=" * 60
    )

    print(
        "ESTIMATE DOWNLOAD COST"
    )

    print(
        "=" * 60
    )


    cost = client.metadata.get_cost(

        dataset=DATASET,

        symbols=[
            SYMBOL
        ],

        schema=SCHEMA,

        start=START,

        end=END,

    )


    print()

    print(
        "dataset:",
        DATASET
    )


    print(
        "symbol:",
        SYMBOL
    )


    print(
        "schema:",
        SCHEMA
    )


    print(
        "start:",
        START
    )


    print(
        "end:",
        END
    )


    print()


    print(
        f"estimated cost: ${cost:.6f}"
    )


    print()


    return cost



# ============================================================
# Download
# ============================================================


def download(
    client
):
    """
    下载官方 MBP-10。


    Databento：

        timeseries.get_range()

    返回：

        DBNStore


    然后：

        DBNStore.to_file()

    保存为：

        .dbn.zst
    """


    DATA_DIR.mkdir(
        parents=True,
        exist_ok=True
    )


    print()

    print(
        "=" * 60
    )

    print(
        "DOWNLOAD MBP-10"
    )

    print(
        "=" * 60
    )


    print()

    print(
        "output:"
    )

    print(
        OUTPUT_FILE
    )

    print()


    data = client.timeseries.get_range(

        dataset=DATASET,

        symbols=[
            SYMBOL
        ],

        schema=SCHEMA,

        start=START,

        end=END,

        stype_in="raw_symbol",

    )


    # ========================================================
    # 保存 DBN.ZST
    # ========================================================

    data.to_file(

        OUTPUT_FILE,

        compression="zstd",

    )


    print()

    print(
        "=" * 60
    )

    print(
        "DOWNLOAD COMPLETE"
    )

    print(
        "=" * 60
    )


    print()

    print(
        "file:"
    )

    print(
        OUTPUT_FILE
    )


    print()


    if OUTPUT_FILE.exists():

        file_size = (
            OUTPUT_FILE.stat().st_size
        )


        print(
            "file size:"
        )

        print(
            f"{file_size:,} bytes"
        )


    return OUTPUT_FILE



# ============================================================
# Validate downloaded file
# ============================================================


def validate_file(
    file_path: Path
):
    """
    下载后重新打开文件。

    验证：

        DBN文件可以正常读取

        Schema基本正确

        至少能够读到第一条记录
    """


    print()

    print(
        "=" * 60
    )

    print(
        "VALIDATE DOWNLOADED FILE"
    )

    print(
        "=" * 60
    )


    store = db.DBNStore.from_file(
        file_path
    )


    count = 0


    first_record = None


    for record in store:

        first_record = record

        count += 1

        break


    if first_record is None:

        raise RuntimeError(
            "Downloaded MBP-10 file contains no records."
        )


    print()

    print(
        "first record:"
    )

    print(
        first_record
    )


    print()

    print(
        "validation:"
    )

    print(
        "OK"
    )



# ============================================================
# Main
# ============================================================


def main():
    """
    Main。
    """


    print()

    print(
        "=" * 60
    )

    print(
        "DATABENTO MBP-10 DOWNLOADER"
    )

    print(
        "=" * 60
    )


    print()

    print(
        "dataset:",
        DATASET
    )


    print(
        "symbol:",
        SYMBOL
    )


    print(
        "schema:",
        SCHEMA
    )


    print(
        "start:",
        START
    )


    print(
        "end:",
        END
    )


    print()


    # ========================================================
    # API key
    # ========================================================

    if not check_api_key():

        sys.exit(1)


    # ========================================================
    # Client
    # ========================================================

    client = create_client()


    # ========================================================
    # Availability
    # ========================================================

    check_dataset_range(
        client
    )


    # ========================================================
    # Cost
    # ========================================================

    estimate_cost(
        client
    )


    # ========================================================
    # 用户安全确认
    #
    # 防止直接产生收费下载
    # ========================================================

    print()

    answer = input(
        "Continue download? [y/N]: "
    )


    if answer.strip().lower() not in (
        "y",
        "yes",
    ):

        print()

        print(
            "Download cancelled."
        )

        return


    # ========================================================
    # Download
    # ========================================================

    output = download(
        client
    )


    # ========================================================
    # Validate
    # ========================================================

    validate_file(
        output
    )


    print()

    print(
        "=" * 60
    )

    print(
        "DONE"
    )

    print(
        "=" * 60
    )



if __name__ == "__main__":

    main()