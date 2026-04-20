from pydantic import BaseModel, Field


class CreateShortUrlRequest(BaseModel):
    long_url: str = Field(description="The long URL to shorten")
    tags: list[str] | None = Field(default=None, description="Tags to associate with the URL")
    custom_slug: str | None = Field(default=None, description="Custom short code")
    valid_until: str | None = Field(
        default=None, description="ISO 8601 datetime when URL expires"
    )
    max_visits: int | None = Field(default=None, description="Maximum number of visits")


class ShortUrlResponse(BaseModel):
    short_url: str = Field(description="The shortened URL")
    short_code: str = Field(description="The short code")
    long_url: str = Field(description="The original long URL")
    date_created: str = Field(description="Creation date in ISO 8601 format")
    tags: list[str] = Field(default_factory=list, description="Associated tags")
    visits_count: int = Field(description="Number of visits")


class ShortUrlDetails(ShortUrlResponse):
    meta: dict | None = Field(default=None, description="URL metadata")


class ShortUrlListResponse(BaseModel):
    data: list[ShortUrlResponse]
    pagination: dict = Field(description="Pagination info")


class TagResponse(BaseModel):
    tag: str = Field(description="Tag name")
    short_urls_count: int = Field(description="Number of URLs with this tag")


class TagListResponse(BaseModel):
    data: list[TagResponse]
