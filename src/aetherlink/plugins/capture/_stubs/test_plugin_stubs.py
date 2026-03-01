
from pydantic import BaseModel


class PluginCapabilities(BaseModel):
    pass

async def Initialize(services):
    return True

async def Start(profile):
    return True

async def Stop():
    return True

async def Shutdown():
    return True

def GetCapabilities() -> PluginCapabilities:
    return PluginCapabilities()
