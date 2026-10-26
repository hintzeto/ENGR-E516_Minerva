# ENGR-E516_Minerva
An AI academic tutor designed to help graduate students manage resources, get instant tutoring access, and receive immediate assignment and project feedback.

## Basic Software Architecture
Minerva uses an Model View Controller (MVC) architecture for multi-node cloud computing. The basic architecture is designed as follows:

```mermaid
architecture-beta
    group view(internet)[View]
    group controller(cloud)[Controller]
    group model(database)[Model]

    service rproxy(server)[Reverse Proxy (Caddy)] in view
    service web(internet)[Website (Streamlit)] in view
    
    service api(server)[API (FastAPI)] in controller
    service task(server)[Task Scheduling/Execution (Redis/Celery)] in controller
    service agent(cloud)[Agent Orchestration (LangGraph)] in controller
    service inference(cloud)[LLM Inference (SGLang)] in controller

    service relational(database)[Relational Database (PostgreSQL)] in model
    service vector(database)[Vector Storage (pgvector)] in model

    rproxy:R --> L:web
    web:B <--> T:api
    api:L <--> R:agent
    api:R <--> L:task
    agent:L <--> R:inference
    api:B <--> T:relational
    api:B <--> T:vector
    relational:R <--> L:vector
```

### Logical Application Split Using Docker Compose Stacks

To keep logical groups of services in Minerva separate and to allow for proper vertical scaling, services will be deployed in docker compose stacks. These stacks also enable reproducibility and transportability between compute instances.

Compose stacks also allow for easy initial testing on a single VM, while allowing for easy decoupling and scaling out to multiple VMs. 

Following is an outline of what each stack will contain:

![Minerva Docker Compose Diagram](docs/images/Minerva-Docker-Compose-Stack-Diagram.png)

*Note: At this time, proper horizontal scaling (dynamically spinning up new VMs) is not in scope. Were that a requirement different services would need to scale differently.*


## Initial Agent Flow

The general flow to get an LLM response to a user is defined as follows:

```mermaid
flowchart TD
    A[User Prompt] --> B(Team Lead Agent)
    B --> C[Tutoring Agent]
    B --> D[Scheduling Agent]
    B --> E[Feedback Agent]
    C --> F[Fact Check Agent]
    D --> F[Fact Check Agent]
    E --> F[Fact Check Agent]
    F --> G[Response to User]
```

