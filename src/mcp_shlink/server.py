from mcp_shlink.tools import mcp


def run() -> None:
    mcp.run(transport="stdio")


if __name__ == "__main__":
    run()
