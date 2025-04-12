# Compmake Python 3.12 Compatibility Fix

## Issue Description

When running tests in the quickapp project with Python 3.12, we encounter the following error:

```
AttributeError: module 'inspect' has no attribute 'getargspec'. Did you mean: 'getargs'?
```

This occurs because compmake is using the deprecated `inspect.getargspec()` function, which was removed in Python 3.12.

## Error Location

The error occurs in the compmake UI module:

```
File "/Users/eric/20sq/mcdp/vendor/compmake/src/compmake/ui/ui.py", line 522, in interpret_single_command
  argspec = inspect.getargspec(function)
```

## Required Fix

Replace `getargspec()` with the newer `getfullargspec()` function. There are two approaches to fix this:

### Option 1: Direct Replacement (Simple)

Replace direct calls to `getargspec()` with `getfullargspec()` and adjust the code to handle the slightly different return values.

```python
# Before
argspec = inspect.getargspec(function)

# After
argspec = inspect.getfullargspec(function)
```

Note: This works if your code doesn't rely on the exact structure of the return value. If it does, see Option 2.

### Option 2: Compatibility Wrapper (Recommended for Backward Compatibility)

Add a utility function to maintain compatibility with both old and new Python versions:

```python
# Add this to an appropriate utility module in compmake (e.g., compmake/utils.py)
def get_arg_spec(function):
    """Compatibility wrapper for inspect.getargspec/getfullargspec"""
    if hasattr(inspect, 'getfullargspec'):
        spec = inspect.getfullargspec(function)
        # Convert to the old format if needed by your code
        return inspect.ArgSpec(
            args=spec.args,
            varargs=spec.varargs,
            keywords=spec.varkw,
            defaults=spec.defaults
        )
    else:
        # For older Python versions
        return inspect.getargspec(function)
```

Then replace all occurrences of `inspect.getargspec(function)` with your new function:

```python
# Before
argspec = inspect.getargspec(function)

# After
from compmake.utils import get_arg_spec  # adjust import path as needed
argspec = get_arg_spec(function)
```

## Files to Modify

Search the compmake codebase for all occurrences of `getargspec`. The main file is:

- `/Users/eric/20sq/mcdp/vendor/compmake/src/compmake/ui/ui.py`

But there may be other instances in the codebase that should also be fixed.

## Testing the Fix

After implementing the fix, run the following test to verify it works:

```bash
cd /Users/eric/20sq/mcdp/vendor/quickapp
python -m pytest src/quickapp/tests/test_dynamic_1.py -v
```

This should no longer show the `inspect.getargspec` error.