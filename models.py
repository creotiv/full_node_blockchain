
from typing import List
from pydantic import BaseModel, Field

"""
Just some Input models for FastApi
"""

class InputModel(BaseModel):
    prev_tx_hash:str
    output_index:int
    address:str
    index:int
    signature:str

class OutputModel(BaseModel):
    amount:int
    address:str
    index:int
    input_hash:str

class TxModel(BaseModel):
    inputs:List[InputModel]
    outputs:List[OutputModel]
    timestamp:int
    class Config:
        arbitrary_types_allowed = True

class BlockModel(BaseModel):
    index:int
    nonce:int
    timestamp:int
    prev_hash:str
    txs:List[TxModel]
    class Config:
        arbitrary_types_allowed = True

class BlocksModel(BaseModel):
    blocks:List[BlockModel]
    class Config:
        arbitrary_types_allowed = True

class NodesModel(BaseModel):
    nodes:List[str]