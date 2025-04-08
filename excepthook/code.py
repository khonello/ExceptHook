from typing import Union, Any, TypedDict
from traceback import extract_tb, format_tb, print_exception, format_exception, format_exception_only, print_exc, format_exc
from importlib.machinery import ModuleSpec
from inspect import Traceback
from importlib.util import spec_from_file_location
from langchain.prompts import PromptTemplate
from langchain.output_parsers import PydanticOutputParser
from langchain_groq import ChatGroq
from pydantic import BaseModel
from dotenv import load_dotenv
from rich.tree import Tree
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn
from rich.text import Text
from rich.syntax import Syntax
import rich
import re
import os
import sys
import builtins
import time
import __main__

load_dotenv()

default_excepthook = sys.excepthook
default_print = builtins.print

builtins.print = rich.print

fix_prompt = PromptTemplate.from_template(
    "Context of problem:\n"
    "{input}\n\n"

    "Your response should not contain any errors. Ignore all comments of this structure: \'#: command\'. Respond strictly in JSON format without markdown or backticks and respond with the following structure:\n"
    "{{\"fix\": \"Fixed python code here\", \"issue\": \"Short feedback on what the problem was. Minimum of 5 words, maximum of 100 words\"}}\n\n"
)

explain_prompt = PromptTemplate.from_template(
    "Context of problem:\n"
    "{input}\n\n"

    "Your response should only be a guide on how to fix the issue, do not provide any solution. If the problem is complex, break the guide into steps. Respond strictly without markdown or backticks and respond with the following structure:\n"
    "{{\"explanation\": \"Explanation here. Maximum of 100 words\"}}\n\n"
)

class FixResponse(BaseModel):
    
    fix: str
    issue: str

class ExplainResponse(BaseModel):

    explanation: str

chat = ChatGroq(model= "llama-3.3-70b-versatile")

fix_parser = PydanticOutputParser(pydantic_object= FixResponse)
explain_parser = PydanticOutputParser(pydantic_object= ExplainResponse)

class WorkSetupReturn(TypedDict):
    
    fix: bool
    enhance: bool
    prompt_input: str
    chain: object
    spec: ModuleSpec
    message: str
    code_combined: str

def main_setup(exception_type: BaseException, exception: BaseException, traceback_type: Union[Traceback, None]) -> WorkSetupReturn:

    codes_list = []
    message = exception.__str__()

    if __main__.__spec__ == None:                       # not running with `python -m module`
        
        spec: ModuleSpec = spec_from_file_location(os.path.basename(__main__.__file__), __main__.__file__)
    else:

        spec: ModuleSpec = __main__.__spec__

    for stack_summary in extract_tb(traceback_type):

        if (stack_summary.filename.__contains__(spec.name)):  
            codes_list += [
                    f" {stack_summary.lineno}\t {stack_summary.line}"
                ]
    else:
        codes_list = codes_list[::-1]

    code_combined = "\n".join(codes_list) + "\n"
    full_rawsource: str | None = None

    with open(spec.origin, "r") as f:
        full_rawsource = f.read()

    matches_iter = re.finditer(r"(?P<FIX>(#:\s?fix))|(?P<ENHANCE>(#:\s?enhance))|(?P<EXPLAIN>(#:\s?explain))", full_rawsource.strip(), flags= re.IGNORECASE)

    fix = None
    enhance = None
    explain = None

    for match in matches_iter:

        match_dict = match.groupdict()
        if match_dict["FIX"]:
            fix = match_dict["FIX"]

        elif match_dict["ENHANCE"]:
            enhance = match_dict["ENHANCE"]

        elif match_dict["EXPLAIN"]:
            explain = match_dict["EXPLAIN"]

    return {
        "fix": fix, "enhance": enhance, "explain": explain, "spec": spec, "message": message, "code_combined": code_combined, "full_rawsource": full_rawsource
    }

def custom_excepthook(exception_type: BaseException, exception: BaseException, traceback_type: Union[Traceback, None] ):

        if hasattr(__main__, '__file__'):                       # we are not in REPL
            
            return_dict: WorkSetupReturn = main_setup(exception_type= exception_type, exception= exception, traceback_type= traceback_type)
            fix, enhance, explain, spec, message, code_combined, full_rawsource = return_dict.values()

            def _enhance():

                traceback_tree = Tree(
                    label= f"[bold red]{exception_type.__qualname__}[/bold red]", style= "bold gray23"
                )

                message_node = traceback_tree.add(":pencil: Reason")
                code_node = traceback_tree.add(":laptop_computer: Code")

                markdown = message_node.add(
                    Panel(
                        Text(
                            text= f"{message.title()}", style= "dark_orange3"
                        )
                    )
                )

                syntax = code_node.add(
                    Panel(
                        Syntax(
                            code= code_combined, lexer= "python", theme= "monokai", line_numbers= False
                        ),
                    )
                )
                print(traceback_tree)

            def _fix():
                
                with Progress(SpinnerColumn(spinner_name= "dots"), TextColumn("{task.description}"), BarColumn()) as fixing_progress:

                    fixing_task = fixing_progress.add_task("[green]Thinking...   ", total= None)
                    
                    prompt_input = f"{{'cause': {code_combined}, 'reason': {message}, 'full_code': {full_rawsource}}}"
                    chain = fix_prompt | chat | fix_parser

                    try:

                        raw_response: FixResponse = chain.invoke({"input": prompt_input})
                        fixing_progress.update(fixing_task, description= "[green]Done Thinking ")

                        with open(spec.origin, "w") as f:
                            f.write(raw_response.fix)
                        time.sleep(1)
                    
                        fixing_progress.update(fixing_task, description= "[green]Done Fixing   ")
                        print(f"\n[dark_orange]NOTE: {raw_response.issue}[/dark_orange]")

                    except Exception:

                        print("[bold red]Something went wrong[/bold red]")


            def _explain():
                
                with Progress(SpinnerColumn(spinner_name= "dots"), TextColumn("{task.description}"), BarColumn()) as explain_progress:

                    explain_task = explain_progress.add_task("[green]Thinking...   ", total= None)
                    
                    prompt_input = f"{{'cause': {code_combined}, 'reason': {message}, 'full_code': {full_rawsource}}}"
                    chain = explain_prompt | chat | explain_parser

                    try:

                        raw_response: ExplainResponse = chain.invoke({"input": prompt_input})
                        explain_progress.update(explain_task, description= "[green]Done Thinking ")

                        split = raw_response.explanation.split(".")

                        combined_lines = None
                        with open(spec.origin, "r") as r:

                            readlines = r.readlines()
                            map_obj = map((lambda line: f"# {line.lstrip(" ")}"), split[:-1])
                            
                            combined_lines = [
                                *["\n".join(map_obj)], "\n\n", *readlines
                            ]

                        combined_code = "".join(combined_lines)
                        final_code = re.sub(re.compile(r"(#:\s?\w+\s*\n)", re.IGNORECASE), "", combined_code)

                        with open(spec.origin, "w") as w:
                            w.write(final_code)

                        time.sleep(1)
                        explain_progress.update(explain_task, description= "[green]Done Explaining")

                    except Exception:

                        print("[bold red]Something went wrong[/bold red]")
                    
            if all([fix, enhance, explain]):

                print_exception(exception)
                print("\n[bold red]Cannot use both fix and explain. Fix provides an explanation in terminal[/bold red]")
            elif all([fix, enhance]):

                _enhance()
                _fix()

            elif all([enhance, explain]):

                _enhance()
                _explain()

            elif all([fix, explain]):

                print_exception(exception)
                print("\n[bold red]Cannot use both fix and explain. Fix provides an explanation in terminal[/bold red]")
            elif fix:
                
                _fix()
            elif enhance:

                _enhance()
            elif explain:

                _explain()
            else:

                print_exception(exception)

        else:
            print_exception(exception)

def custom_displayhook(obj: str | None):

    if obj:
        print(obj)

sys.excepthook = custom_excepthook
sys.displayhook = custom_displayhook
