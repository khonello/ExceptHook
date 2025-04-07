from typing import Generic, Any, Union
from traceback import extract_tb, format_tb, print_exception, format_exception, format_exception_only, print_exc, format_exc
from importlib.machinery import ModuleSpec
from inspect import Traceback
from importlib.util import spec_from_file_location
from langchain.prompts import PromptTemplate
from langchain.memory import ConversationBufferMemory
from langchain.output_parsers import PydanticOutputParser
from langchain.chains import LLMChain
from langchain_groq import ChatGroq
from pydantic import BaseModel
from dotenv import load_dotenv
from rich.tree import Tree
from rich.panel import Panel
from rich.progress import Progress, ProgressType, ProgressSample
from rich.text import Text
from rich.syntax import Syntax
from rich.markdown import Markdown
import rich
import re
import os
import sys
import builtins
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

def custom_excepthook(exception_type: BaseException, exception: BaseException, traceback_type: Union[Traceback, None] ):

    if hasattr(__main__, '__file__'):                       # we are in REPL

        codes_list = []

        exception_typename = exception_type.__qualname__
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

        traceback_tree = Tree(
            label= f"[bold red]{exception_typename}[/bold red]", style= "bold gray23"
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

        matches_iter = re.finditer(r"(?P<FIX>(#:\s?fix))|(?P<ENHANCE>(#:\s?enhance))", full_rawsource.strip(), flags= re.IGNORECASE)

        fix = False
        enhance = False

        for match in matches_iter:

            match_dict = match.groupdict()
            if match_dict["FIX"]:
                fix = match_dict["FIX"]

            elif match_dict["ENHANCE"]:
                enhance = match_dict["ENHANCE"]

        prompt_input = f"{{'cause': {code_combined}, 'reason': {message}, 'full_code': {full_rawsource}}}"
        chain = prompt | chat | parser

        if all([fix, enhance]):

            raw_response = chain.invoke({"input": prompt_input})
            print(traceback_tree)   
            print(f"[dark_orange]NOTE: {raw_response.issue}[/dark_orange]")

            with open(spec.origin, "w") as f:
                f.write(raw_response.fix)

        elif fix:
            
            raw_response = chain.invoke({"input": prompt_input})
            print(f"[dark_orange]NOTE: {raw_response.issue}[/dark_orange]")

            with open(spec.origin, "w") as f:
                f.write(raw_response.fix)

        elif enhance:

            print(traceback_tree)
        else:

            print_exception(exception)

    else:
        print_exception(exception)

def custom_displayhook(obj: str | None):

    if obj:
        print(obj)

sys.excepthook = custom_excepthook
sys.displayhook = custom_displayhook
