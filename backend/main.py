from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

app = FastAPI()

origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

### ML MODEL START


# ! pip install transformers
# ! pip install datasets

import os
import clang
from clang.cindex import *
from copy import deepcopy
import time

import numpy as np
import pandas as pd

from transformers import AutoModelForSequenceClassification, AutoTokenizer, pipeline

Config.set_library_file("/home/dipu/anaconda3/lib/python3.9/site-packages/clang/native/libclang.so")

id2label = {0: "CORRECT", 1: "BUGGY"}
label2id = {"CORRECT": 0, "BUGGY": 1}

tokenizer = AutoTokenizer.from_pretrained("./function-args-swap-bug/tokenizer")

function_args_swap_bug_model = AutoModelForSequenceClassification.from_pretrained(
                                                            "./function-args-swap-bug/model",
                                                            num_labels=2,
                                                            id2label=id2label,
                                                            label2id=label2id)

wrong_binary_operator_bug_model = AutoModelForSequenceClassification.from_pretrained(
                                                            "./wrong-binary-operator-bug/model",
                                                            num_labels=2,
                                                            id2label=id2label,
                                                            label2id=label2id)

# function args swap bug classifier
fosb_classifier = pipeline("text-classification", model=function_args_swap_bug_model, tokenizer=tokenizer)

# wrong binary operator bug classifier
wbob_classifier = pipeline("text-classification", model=wrong_binary_operator_bug_model, tokenizer=tokenizer)


def generate_ast(code):
    with open('evaluation.c', 'w') as f:
        f.write(code)
    
    index = clang.cindex.Index.create()
    root_cursor = index.parse('evaluation.c').cursor

    return root_cursor


def generate_fasb_prediction(root_cursor):

    def get_function_params(root, function_name, result):
        for node in root.walk_preorder():
            try:
                if node.kind == CursorKind.FUNCTION_DECL \
                and node.spelling == function_name:
                    # loop through its children and only append details of parameter node
                    for c in node.get_children():
                        if c.kind == CursorKind.PARM_DECL:
                            result.append({"name": c.spelling, 
                                        "data_type": c.type.spelling})
                    return
            except ValueError as e:
                # print("Error:", e)
                pass
    
    def get_called_functions(root, result):
        for node in root.walk_preorder():
            try:
                if node.kind == CursorKind.CALL_EXPR:
                    # "location": node.extent
                    current_function = {"name": node.spelling, "return_type": node.type.spelling, "args": [], "location": node.extent}

                    for c in node.get_arguments():
                        current_arg = "".join([x.spelling for x in list(c.get_tokens())]) if len(list(c.get_tokens())) > 0 else c.spelling

                        current_function["args"].append({"name": current_arg, "data_type": c.type.spelling, "cursor_kind": c.kind})
                        # current_function["args"].append({"name": c.spelling, "data_type": c.type.spelling, "cursor_kind": c.kind})
                        # print(node.location)

                    current_param_list = []
                    if len(current_function["args"]) == 2 and \
                        (current_function["args"][0]["data_type"] == current_function["args"][1]["data_type"]):
                        get_function_params(root, node.spelling, current_param_list)
                    current_function["params"] = current_param_list

                    result.append(current_function)

            except ValueError:
                pass

    function_list = []
    function_args_swap_bug_data = []
    get_called_functions(root_cursor, function_list)

    for function in function_list: 
        if len(function["args"]) == 2 and \
            (function["args"][0]["data_type"] == function["args"][1]["data_type"]) and \
            (function["args"][0]["name"] != function["args"][1]["name"]):
            
            sample = [function["name"], function["args"][0]["name"], function["args"][1]["name"],
                            function["args"][0]["data_type"]]
            
            if(len(function["params"]) == 2):
                sample.append(function["params"][0]["name"])
                sample.append(function["params"][1]["name"])
            else:
                sample.append("")
                sample.append("")
                
            loc = function["location"]
            sample += [str(loc.start.line), str(loc.start.column), str(loc.end.line), str(loc.end.column)]
            
            function_args_swap_bug_data.append(sample)

    df = pd.DataFrame(function_args_swap_bug_data,
                columns=["function_name", "arg1", "arg2", "arg_type",
                        "param1", "param2", "start_line", "start_column",
                        "end_line", "end_column"])

    df['full_text'] = df['function_name'] + tokenizer.sep_token + df['arg1'] +\
                        tokenizer.sep_token + df['arg2'] + tokenizer.sep_token +\
                        df['arg_type'] + tokenizer.sep_token + df['param1'] +\
                        tokenizer.sep_token + df['param2']

    fosb_result = fosb_classifier(list(df.full_text))

    df.drop(columns=["arg_type", "param1", "param2", "full_text"], inplace=True)

    df["label"] = [label2id[element["label"]] for element in fosb_result]
    df["probability"] = [element["score"] for element in fosb_result]

    return [dict(row) for index, row in df.iterrows()]


def generate_wbob_prediction(root_cursor):
    def get_binary_expressions(node, parent, grandparent, result):
        try:
            if node.kind == CursorKind.BINARY_OPERATOR:

                children_list = [i for i in node.get_children()]

                if len(children_list) == 2:
                    left_offset = len([i for i in children_list[0].get_tokens()])
                    operator_name = [i for i in node.get_tokens()][left_offset].spelling

                    current_operation = {
                                            "operator": operator_name,
                                            "operands": [],
                                            "parent": parent.kind.name if parent is not None else "",
                                            "grandparent": grandparent.kind.name if grandparent is not None else "",
                                            "location": node.extent
                                        }

                    for c in children_list:
                        """ To only allow binary operation between single operators on left and right """
                        if c.kind == CursorKind.BINARY_OPERATOR or c.kind == CursorKind.PAREN_EXPR:
                            current_operation = {}
                            break

                        operand = "".join([x.spelling for x in list(c.get_tokens())]) if len(list(c.get_tokens())) > 0 else c.spelling
                        
                        if len(operand) >= 3 and operand.startswith('\"') and operand.endswith('\"'):
                            operand = '\"' + current_arg[1:-1].replace('\"', "\"\"") + '\"'

                        current_operation["operands"].append({"name": operand, "data_type": c.type.spelling, "cursor_kind": c.kind.name})

                    if current_operation != {}:
                        result.append(current_operation)
            
            for c in node.get_children():
                get_binary_expressions(c, node, parent, result)

        except Exception as e:
            pass

    binary_operation_list = []
    wrong_binary_operator_bug_data = []
    get_binary_expressions(root_cursor, None, None, binary_operation_list)

    for operation in binary_operation_list:
        loc = operation["location"]
                
        sample = [operation["operands"][0]["name"], operation["operator"], operation["operands"][1]["name"],
                    operation["operands"][0]["data_type"], operation["operands"][1]["data_type"],
                    operation["parent"], operation["grandparent"],
                    str(loc.start.line), str(loc.start.column), str(loc.end.line), str(loc.end.column)]

        wrong_binary_operator_bug_data.append(sample)

    df = pd.DataFrame(wrong_binary_operator_bug_data,
                columns=["left", "operator", "right", "type_left", "type_right", "parent", "grandparent",
                "start_line", "start_column", "end_line", "end_column"])

    df = df.loc[(~df.operator.isin([",", "="]))]
    df = df.reset_index(drop=True)

    df['full_text'] = df['left'] + tokenizer.sep_token + df['operator'] + tokenizer.sep_token + df['right'] +\
                        tokenizer.sep_token + df['type_left'] + tokenizer.sep_token + df['type_right'] +\
                        tokenizer.sep_token + df['parent'] + tokenizer.sep_token + df['grandparent']

    wbob_result = wbob_classifier(list(df.full_text))

    df.drop(columns=["type_left", "type_right", "parent", "grandparent", "full_text"], inplace=True)

    df["label"] = [label2id[element["label"]] for element in wbob_result]
    df["probability"] = [element["score"] for element in wbob_result]

    return [dict(row) for index, row in df.iterrows()]


#### ML MODEL END


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

    # converting output to python dictionary for JSON conversion
    output = {"analysis": {
        "function_args_swap_bug": fasb_prediction,
        "wrong_binary_operator_bug": wbob_prediction
    }}
    
    # sending JSON response to client-side app
    return JSONResponse(content=str(output))