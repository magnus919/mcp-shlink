from mcp_shlink.tools import mcp


def run() -> None:
    mcp.run(transport="streamable-http")


if __name__ == "__main__":
    run()
