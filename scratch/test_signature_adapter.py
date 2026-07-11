import inspect
from functools import wraps

def _make_safe_handler(fn):
    try:
        sig = inspect.signature(fn)
        params = list(sig.parameters.values())
    except (ValueError, TypeError):
        return fn

    takes_args_dict = False
    if params:
        first_param = params[0]
        if first_param.name in {"args", "arg", "payload", "dict_args", "kwargs"} or first_param.kind == inspect.Parameter.VAR_POSITIONAL:
            takes_args_dict = True
        elif len(params) == 1 and first_param.name == "args":
            takes_args_dict = True

    has_var_keyword = any(p.kind == inspect.Parameter.VAR_KEYWORD for p in params)

    if inspect.iscoroutinefunction(fn):
        @wraps(fn)
        async def safe_wrapper_async(args, **kwargs):
            fn_kwargs = {}
            if has_var_keyword:
                fn_kwargs.update(kwargs)
            else:
                for k, v in kwargs.items():
                    if k in sig.parameters:
                        fn_kwargs[k] = v
            if takes_args_dict:
                # Prioritize kwargs from system
                return await fn(args, **fn_kwargs)
            else:
                fn_args = {}
                for k, v in args.items():
                    if k in sig.parameters:
                        fn_args[k] = v
                # Merge: fn_args (LLM params) overrides fn_kwargs (system context)
                combined = {**fn_kwargs, **fn_args}
                return await fn(**combined)
        return safe_wrapper_async
    else:
        @wraps(fn)
        def safe_wrapper(args, **kwargs):
            fn_kwargs = {}
            if has_var_keyword:
                fn_kwargs.update(kwargs)
            else:
                for k, v in kwargs.items():
                    if k in sig.parameters:
                        fn_kwargs[k] = v
            if takes_args_dict:
                return fn(args, **fn_kwargs)
            else:
                fn_args = {}
                for k, v in args.items():
                    if k in sig.parameters:
                        fn_args[k] = v
                combined = {**fn_kwargs, **fn_args}
                return fn(**combined)
        return safe_wrapper

# Tests
def test_args_dict():
    def my_handler(args, task_id=None):
        return f"args: {args}, task_id: {task_id}"
    
    safe = _make_safe_handler(my_handler)
    res = safe({"cmd": "run"}, task_id="123", session_id="abc")
    assert res == "args: {'cmd': 'run'}, task_id: 123"

def test_kw_unpacked():
    def screenshot(region=None, task_id=None):
        return f"region: {region}, task_id: {task_id}"
        
    safe = _make_safe_handler(screenshot)
    res = safe({"region": "0,0,10,10"}, task_id="123", session_id="abc")
    assert res == "region: 0,0,10,10, task_id: 123"

def test_no_args():
    def clipboard_get():
        return "empty"
        
    safe = _make_safe_handler(clipboard_get)
    res = safe({}, task_id="123")
    assert res == "empty"

def test_overlapping_session_id():
    def get_current_persona(session_id=None):
        return f"session: {session_id}"
        
    safe = _make_safe_handler(get_current_persona)
    # LLM passes session_id, and system also passes it
    res = safe({"session_id": "llm-session"}, session_id="sys-session")
    assert res == "session: llm-session"

test_args_dict()
test_kw_unpacked()
test_no_args()
test_overlapping_session_id()
print("All signature adapter tests passed!")
