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

prompt = PromptTemplate.from_template(
    "Context of problem:\n"
    "{input}\n\n"

    "Your response should not contain any errors. Ignore all comments of this structure: \'#: command\'. Respond strictly in JSON format without markdown or backticks and respond with the following structure:\n"
    "{{\"fix\": \"Fixed python code here\", \"issue\": \"Short feedback on what the problem was. Minimum of 5 words, maximum of 100 words\"}}\n\n"
)

class Response(BaseModel):

    fix: str
    issue: str

chat = ChatGroq(model="llama-3.3-70b-versatile")
parser = PydanticOutputParser(pydantic_object= Response)

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

    matches_iter = re.finditer(r"(?P<FIX>(#:\s?fix))|(?P<ENHANCE>(#:\s?enhance))", full_rawsource.strip(), flags= re.IGNORECASE)

    fix = False
    enhance = False

    for match in matches_iter:

        match_dict = match.groupdict()
        if match_dict["FIX"]:
            fix = match_dict["FIX"]

        elif match_dict["ENHANCE"]:
            enhance = match_dict["ENHANCE"]

    return {
        "fix": fix, "enhance": enhance, "spec": spec, "message": message, "code_combined": code_combined, "full_rawsource": full_rawsource
    }

def custom_excepthook(exception_type: BaseException, exception: BaseException, traceback_type: Union[Traceback, None] ):

        if hasattr(__main__, '__file__'):                       # we are not in REPL
            
            return_dict = main_setup(exception_type= exception_type, exception= exception, traceback_type= traceback_type)
            fix, enhance, spec, message, code_combined, full_rawsource = return_dict.values()

            def _enhancing():

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

            def _fixing():
                
                with Progress(SpinnerColumn(spinner_name= "dots"), TextColumn("{task.description}"), BarColumn()) as llm_progress:

                    llm_task = llm_progress.add_task("[green]Thinking...", total= None)
                    
                    prompt_input = f"{{'cause': {code_combined}, 'reason': {message}, 'full_code': {full_rawsource}}}"
                    chain = prompt | chat | parser

                    raw_response: Response = chain.invoke({"input": prompt_input})
                    llm_progress.update(llm_task, description= "Done Thinking ")

                with Progress(SpinnerColumn(spinner_name= "dots"), TextColumn("{task.description}"), BarColumn()) as fix_progress:

                    fix_task = fix_progress.add_task("[green]Fixing...  ", total= None)
                    with open(spec.origin, "w") as f:
                        
                        f.write(raw_response.fix)  
                    fix_progress.update(fix_task, description= "Done Fixing   ")
                     
                print(f"\n[dark_orange]NOTE: {raw_response.issue}[/dark_orange]")

            if all([fix, enhance]):

                _enhancing()
                _fixing()
            elif fix:
                
                _fixing()
            elif enhance:

                _enhancing()
            else:

                print_exception(exception)

        else:
            print_exception(exception)

def custom_displayhook(obj: str | None):

    if obj:
        print(obj)

sys.excepthook = custom_excepthook
sys.displayhook = custom_displayhook


