# Stubs for luigi.task (Python 3.5)
#
# NOTE: This dynamically typed stub was automatically generated by stubgen.

from typing import Any, Dict, Generic, Iterable, List, Optional, TypeVar, Type, Union

from .target import Target

Parameter = ...  # type: Any
logger = ...  # type: Any
TASK_ID_INCLUDE_PARAMS = ...  # type: int
TASK_ID_TRUNCATE_PARAMS = ...  # type: int
TASK_ID_TRUNCATE_HASH = ...  # type: int
TASK_ID_INVALID_CHAR_REGEX = ...  # type: Any

def namespace(namespace: Optional[Any] = ..., scope: str = ...): ...
def auto_namespace(scope: str = ...): ...
def task_id_str(task_family, params): ...

class BulkCompleteNotImplementedError(NotImplementedError): ...

_R = TypeVar('_R')
_I = TypeVar('_I')
_O = TypeVar('_O')
_T = TypeVar('_T')

class Task(Generic[_R, _I, _O]):
    priority = ...  # type: int
    disabled = ...  # type: bool
    resources = ...  # type: Any
    worker_timeout = ...  # type: Any
    max_batch_size = ...  # type: Any
    @property
    def batchable(self): ...
    @property
    def retry_count(self): ...
    @property
    def disable_hard_timeout(self): ...
    @property
    def disable_window_seconds(self): ...
    @property
    def owner_email(self): ...
    @property
    def use_cmdline_section(self): ...
    @classmethod
    def event_handler(cls, event): ...
    def trigger_event(self, event, *args, **kwargs): ...
    @property
    def task_module(self): ...
    task_namespace = ...  # type: Any
    @classmethod
    def get_task_namespace(cls): ...
    @property
    def task_family(self): ...
    @classmethod
    def get_task_family(cls): ...
    @classmethod
    def get_params(cls): ...
    @classmethod
    def batch_param_names(cls): ...
    @classmethod
    def get_param_names(cls, include_significant: bool = ...) -> List[str]: ...
    @classmethod
    def get_param_values(cls, params, args, kwargs): ...
    param_args = ...  # type: Any
    param_kwargs = ...  # type: Any
    task_id = ...  # type: str
    set_tracking_url = ...  # type: Any
    set_status_message = ...  # type: Any
    def __init__(self, *args, **kwargs) -> None: ...
    def initialized(self): ...
    @classmethod
    def from_str_params(cls: Type[_T], params_str: Dict[str, str]) -> _T: ...
    def to_str_params(self, only_significant: bool = ...): ...
    def clone(self, cls: Optional[Any] = ..., **kwargs): ...
    def __hash__(self): ...
    def __eq__(self, other): ...
    def complete(self) -> bool: ...
    @classmethod
    def bulk_complete(cls, parameter_tuples): ...
    def output(self) -> _O: ...
    def requires(self) -> _R: ...
    def process_resources(self): ...
    def input(self) -> _I: ...
    def deps(self): ...
    def run(self) -> None: ...
    def on_failure(self, exception): ...
    def on_success(self): ...
    def no_unpicklable_properties(self): ...

class MixinNaiveBulkComplete:
    @classmethod
    def bulk_complete(cls, parameter_tuples): ...

class ExternalTask(Task[_R, _I, _O]):
    run = ...  # type: Any

def externalize(taskclass_or_taskobject): ...

class WrapperTask(Task[_R, _I, _O]):
    def complete(self): ...

class Config(Task[_R, _I, _O]): ...

def getpaths(struct): ...
def flatten(struct: Union[Dict[Any, _O], Iterable[_O], _O]) -> List[_O]: ...
def flatten_output(task): ...