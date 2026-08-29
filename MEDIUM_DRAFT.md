# Building PokéGraph: My First Steps into AI Engineering

*From a public API to a reliable knowledge graph—and the road from there to RAG and an AI agent.*

> Working draft. The repository and the examples will evolve as the project moves beyond ingestion.

I am starting an AI engineering learning path by building something small enough to understand end to end: an AI agent that can answer questions about Pokémon.

The subject is deliberately playful, but the engineering problems are real. Before an agent can answer a question reliably, I need to decide what data it can use, how that data should be represented, how to preserve its provenance, and how to test whether the answer is grounded in reality.

This article is the first checkpoint in that journey. At this point, I have not built the agent or the RAG layer yet. I have built the data foundation that those pieces will depend on.

## The first lesson: start with the data

The initial temptation in an AI project is to start with a chat interface and add a model. I am taking the opposite route: first understand the data and create a dependable representation of it.

The initial source is [PokéAPI](https://pokeapi.co/), accessed through [PokeLance](https://github.com/FallenDeity/PokeLance). PokéAPI is a useful starting point because it is public, structured, and rich enough to expose the first important challenge: real APIs are not flat tables.

A Pokémon response is connected to species, types, abilities, moves, game versions, encounter locations, and evolution chains. Some of those resources contain further references. If I simply copied each response into a document, I would either duplicate a lot of information or lose the relationships that make the data useful.

That led to the first architectural decision: use Neo4j as the system of record for the structured Pokémon knowledge graph.

## Modeling the world as a graph

The ingestion package now creates an initial graph with entities such as:

- `Pokemon` and `PokemonSpecies`
- `Type`, `Ability`, and `Move`
- `GameVersion` and `VersionGroup`
- `Region`, `Location`, and `LocationArea`
- `Encounter` and `EncounterMethod`
- `EvolutionChain` and `Item`
- `LearnsetEntry` and `MoveLearnMethod`
- `Source` for provenance

The relationships are as important as the nodes. For example, a Pokémon can `HAS_TYPE`, `HAS_ABILITY`, `CAN_LEARN` a move, `HAS_ENCOUNTER` records, and `SPECIES`-link to its species. A learnset entry connects the Pokémon to a move, version group, and learning method. An encounter connects it to a location area, game version, and encounter method.

This gives us a structure that can answer questions through traversal rather than through a collection of unrelated text fragments. Questions such as “Which Pokémon can learn this move in a particular game generation?” or “Where can this Pokémon be encountered?” map naturally to graph patterns.

## Flattening nested API data without throwing away meaning

One of the most useful design decisions so far was separating the simple relationship from the detailed record.

For a quick question, `Pokemon -[:CAN_LEARN]-> Move` is convenient. But a move is not learned in only one way. The same move may be learned at different levels, through a machine, or in different version groups. Those details belong on a separate `LearnsetEntry` node, connected through:

```text
Pokemon -[:HAS_LEARNSET_ENTRY]-> LearnsetEntry -[:TEACHES]-> Move
                                      |
                                      +-- IN_VERSION_GROUP -> VersionGroup
                                      +-- BY_LEARN_METHOD -> MoveLearnMethod
```

This is a small example of data curation: deciding which information is a shortcut and which information is part of the canonical record. The ingestion code flattens every relevant combination of Pokémon, move, version group, method, level, and order into a stable synthetic identifier.

Encounters require a similar treatment. The API nests locations, versions, and encounter details, so the pipeline first turns those records into rows and then writes the graph relationships in batches. The synthetic IDs make repeated ingestion safe and prevent the same logical record from being inserted multiple times.

## Making ingestion repeatable

The goal is not just to load the data once. It is to be able to run the pipeline again after changing the model, adding a source, or recovering from a partial failure.

The current ingestion process does a few things to support that:

- It applies Neo4j uniqueness constraints before loading data.
- It uses stable API IDs for node identity and deterministic IDs for detailed records and evolution relationships.
- It uses `MERGE` so re-running a load updates existing records instead of blindly duplicating them.
- It writes large relationship collections in transaction batches.
- It caches repeated enrichment requests for locations, versions, types, and evolution chains during a run.
- It supports loading a small named subset, such as `pikachu`, for fast local feedback.
- It continues through the catalog when one Pokémon fails and reports successes and failures in a live progress display.

This reliability work is not as visible as a chat demo, but it is already changing how I think about AI engineering. If the underlying data load is opaque or non-repeatable, debugging an eventual model answer becomes much harder.

## Provenance is part of the data model

The graph includes a `Source` node for PokéAPI, and detailed learnset records retain their source URL and retrieval timestamp. This is the beginning of a larger requirement: answers should be traceable back to the data that supports them.

That matters even in a Pokémon project. When the future agent says that a Pokémon can learn a move, I want to know which version group and method it is referring to—and eventually which source record supports the answer. In a production system, provenance is not an optional annotation added at the end. It affects the schema from the start.

## What exists today

The repository currently contains:

- A Python package for PokéAPI-to-Neo4j ingestion.
- Idempotent schema creation and verification for the ingest identity indexes.
- Writers for Pokémon, learnsets, encounters, evolution chains, types, and source links.
- A small test suite covering learnset extraction, stable IDs, duplicate move handling, and incomplete API details.
- Command-line entry points for schema verification and ingestion.

In a warm Aura database, a short run containing Pikachu has taken about two minutes. The time is currently dominated by enrichment of location hierarchies, which is a useful reminder that network shape and API calls can matter as much as database writes.

The code is intentionally still an MVP. Curated project-specific data such as trainers, teams, and progression is not in the graph yet, because it does not come from PokéAPI and needs a separate data design.

## Where the AI engineering begins

The next stages will build on this foundation:

1. **Curate additional data.** Add project-owned datasets for trainers, teams, and progression, with clear rules for what is authoritative and how it is versioned.
2. **Add retrieval.** Combine graph queries with document retrieval for information that is better represented as text—rules, strategy notes, and explanatory content. This is where chunking, embeddings, metadata filters, and citation behavior enter the project.
3. **Build the agent.** Let a language model decide when to use a graph query, when to retrieve documents, and when to ask a follow-up question instead of guessing.
4. **Evaluate the system.** Create representative questions, expected answer properties, retrieval checks, and regression tests. A convincing demo is not the same as a reliable system.

The likely end state is not “RAG instead of a graph.” It is a combination: the graph for precise entities and relationships, retrieved documents for context and explanations, and an agent that coordinates the two.

## The main lesson so far

The first milestone of an AI application is often not the model. It is a trustworthy information layer.

By starting with ingestion, schema design, identity, provenance, and tests, I am learning the parts of AI engineering that are easy to hide behind a prompt: selecting and curating data, representing it in a way that supports the product, and creating feedback loops when reality is messy.

This is where PokéGraph stands today. The next article—or the next section of this one—will move from “can I load and query the world?” to “can an AI system use that world accurately?”

## Follow along

The full code for this stage is available in the project repository: **[add GitHub URL before publishing]**.

The project is still being built in public. The goal is to document the decisions, failed experiments, and trade-offs—not just the final architecture.
