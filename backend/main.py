from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from models import (
    generate_ast,
    generate_fasb_prediction,
    generate_wbob_prediction,
    generate_opb_prediction,
)

app = FastAPI()

origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class InputItem(BaseModel):
    code: str = None


# POST request endpoint for "/analyze" path
@app.post("/analyze")
async def analyze(inputItem: InputItem):
    code = inputItem.code

    # get cursor of root node of AST
    ast_root_cursor = generate_ast(code)
    # get prediction for function args swap bug
    fasb_prediction = generate_fasb_prediction(ast_root_cursor)
    # get prediction for wrong binary operator bug
    wbob_prediction = generate_wbob_prediction(ast_root_cursor)
    # get prediction for operator presedence bug
    opb_prediction = generate_opb_prediction(ast_root_cursor)

    # converting output to python dictionary for JSON conversion
    output = {
        "analysis": {
            "function_args_swap_bug": fasb_prediction,
            "wrong_binary_operator_bug": wbob_prediction,
            "operator_precedence_bug": opb_prediction,
        }
    }

    # sending response to client-side app
    return output
