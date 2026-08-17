# Security

Student submissions are untrusted code. OpenGrader uses Docker as a practical MVP
boundary, but Docker containers are not equivalent to dedicated virtual machines.

## Default controls

For every test, OpenGrader:

- starts a new container and removes it afterward;
- disables networking;
- applies memory, CPU, and process-count limits;
- makes the container root filesystem read-only;
- mounts the submitted folder read-only;
- copies the submission into a fresh temporary in-container workspace; and
- enforces a host-side timeout, force-removing timed-out containers.

Do not mount the Docker socket, credentials, SSH agents, or sensitive host paths
into grading containers. Use narrowly built, pinned images; keep the host kernel
and Docker current; and run production grading on disposable, dedicated workers.
Image tags in assignment files are mutable, so production systems should pin
images by digest.

## Local mode

`--no-docker` runs shell commands directly as the current OS user. A disposable
copy protects the original submission folder from ordinary writes, but the code
can still read, modify, or delete anything that user can access and can use the
network. Only use local mode for trusted fixtures.

## Known MVP limitations

- Assignment authors are trusted; their image and commands are executed as
  configured.
- Output size is not capped, and very large output may consume host memory.
- Docker daemon authorization is outside OpenGrader.
- Strong multi-tenant deployments need worker isolation, image policy, quotas,
  centralized audit logs, and additional sandboxing such as microVMs.

Report vulnerabilities privately to the project maintainers rather than opening
a public issue containing exploit details.

