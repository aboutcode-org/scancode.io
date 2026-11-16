# `aboutcode.pipeline`

Define and run pipelines.

## Install

```bash
pip install aboutcode.pipeline
```

### Define and execute a pipeline

```python
from aboutcode.pipeline import BasePipeline


class PrintMessages(BasePipeline):
    @classmethod
    def steps(cls):
        return (cls.step1,)

    def step1(self):
        print("Message from step1")


PrintMessages().execute()
```

### Options and steps selection

```python
from aboutcode.pipeline import BasePipeline
from aboutcode.pipeline import optional_step


class PrintMessages(BasePipeline):
    @classmethod
    def steps(cls):
        return (cls.step1, cls.step2)

    def step1(self):
        print("Message from step1")

    @optional_step("foo")
    def step2(self):
        print("Message from step2")


# Execute pipeline with group selection
run = PrintMessages(selected_groups=["foo"])
exitcode, error = run.execute()

# Execute pipeline with steps selection
run = PrintMessages(selected_steps=["step1"])
exitcode, error = run.execute()
```

### Post steps

Post steps run at the end of the pipeline, even when a previous step failed.
Use them for cleanup.

```python
from aboutcode.pipeline import BasePipeline


class PrintMessages(BasePipeline):
    @classmethod
    def steps(cls):
        return (cls.step1,)

    @classmethod
    def get_post_steps(cls):
        return (cls.cleanup,)

    def step1(self):
        raise ValueError("Failure in step1")

    def cleanup(self):
        print("Cleanup runs after the step1 failure")
```
