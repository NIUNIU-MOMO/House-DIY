from pydantic import BaseModel


class RenderRecordRead(BaseModel):
    room_id: str
    room_name: str
    filename: str
    prompt: str
    negative: str = ""
    workflow: str = "flux_interior_t2i_api"
    created_at: str
    image_url: str


class RenderManifestRead(BaseModel):
    rooms: list[RenderRecordRead]
