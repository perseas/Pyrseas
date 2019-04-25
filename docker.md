Turns out we need a custom image to make postgres work here

```bash
> docker build -t dchangdevoted/pyrseas-postgres:1.0.0 - < Dockerfile.postgres
> docker login
> docker push dchangdevoted/pyrseas-postgres:1.0.0
```

