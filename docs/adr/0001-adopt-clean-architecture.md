# ADR-0001: Adopt Clean Architecture for Backend Refactoring

## Status

**Proposed**

## Date

2026-01-18

## Context

The Portfolio Tracker backend has grown to 35+ service files, 14 ORM models, and 12 routers. While functional, the codebase exhibits several architectural concerns:

### Current Pain Points

1. **Fat Services**: Some services like `ibkr_parser.py` (~48KB) mix parsing logic, validation, data transformation, and persistence concerns.

2. **No Clear Domain Boundaries**: Services aren't organized by business domain. Import logic, portfolio calculations, and pricing are intermingled.

3. **ORM Coupling**: Business logic directly depends on SQLAlchemy models. This makes unit testing difficult (requires database) and couples domain rules to persistence details.

4. **Inconsistent Layering**: Some routers contain query logic that should be in services. No clear separation between "what to do" (use cases) and "how to do it" (infrastructure).

5. **Multi-Currency Complexity**: Currency conversion is scattered across multiple services rather than centralized in a value object.

### What Works Well

- **Broker Parser Strategy**: `BaseBrokerParser` with `IBKRParser`, `MeitavParser` implementations follows Strategy pattern well.
- **Parser Registry**: `BrokerParserRegistry` implements Factory pattern correctly.
- **Staged Imports**: Validation before commit is well-designed.
- **FastAPI Dependency Injection**: `Depends(get_db)` provides clean session management.

### Business Context

- **Team Size**: Solo developer (currently)
- **Change Frequency**: Active development with new features planned
- **Criticality**: Financial data requires correctness guarantees
- **Performance**: Not a primary concern (personal portfolio tracking)

## Decision Drivers

* **Testability**: Must be able to test business logic without database
* **Maintainability**: Easier to understand and modify code
* **Correctness**: Financial calculations must be reliable
* **Extensibility**: New brokers, asset types, and features planned
* **Pragmatism**: Solo project, avoid over-engineering

## Considered Options

### Option 1: Clean Architecture (Full)

Restructure into domain/, use_cases/, adapters/, infrastructure/ layers with strict dependency rules.

**Pros:**
- Maximum testability (domain has zero dependencies)
- Clear separation of concerns
- Framework-independent core logic
- Well-documented pattern with community support

**Cons:**
- Significant refactoring effort (estimated 40+ files affected)
- More boilerplate (interfaces, mappers, DTOs)
- Overkill for solo project?
- Risk of over-abstraction

### Option 2: Lightweight Domain Layer

Extract only domain entities and value objects. Keep services mostly as-is but inject repository interfaces.

**Pros:**
- Lower effort (10-15 files)
- Improves testability of core calculations
- Preserves working code
- Can evolve toward full Clean Architecture later

**Cons:**
- Partial solution, some coupling remains
- May create inconsistent patterns
- "Middle ground" can become messy

### Option 3: Service Reorganization Only

Group existing services by domain (portfolio/, import/, pricing/) without introducing new abstractions.

**Pros:**
- Minimal code changes
- Immediate clarity improvement
- No new patterns to learn
- Low risk

**Cons:**
- Doesn't address ORM coupling
- Doesn't improve testability
- Doesn't solve fat service problem
- Kicks the can down the road

### Option 4: Status Quo

Leave architecture as-is, focus on features.

**Pros:**
- Zero effort
- No risk of breaking working code
- Ship features faster

**Cons:**
- Technical debt accumulates
- Testing remains difficult
- Onboarding (future contributors) harder
- Bugs in financial calculations harder to catch

## Decision

**Option 2: Lightweight Domain Layer** (with path to Option 1)

Start with targeted extractions that provide immediate value:

1. **Value Objects**: `Money`, `Ticker`, `DateRange` - centralize validation
2. **Repository Interfaces**: For `Holding`, `Transaction`, `Asset` - enable testing
3. **One Use Case**: Convert `PortfolioReconstructionService` to demonstrate pattern
4. **Domain Entities**: Pure Python classes for core concepts (no SQLAlchemy)

This provides 80% of the benefit with 30% of the effort. If successful, expand toward full Clean Architecture.

## Rationale

1. **Risk Mitigation**: Smaller changes are easier to validate and rollback.

2. **Proof of Concept**: Converting one service demonstrates viability before committing fully.

3. **Pragmatic for Solo Project**: Full Clean Architecture may be over-engineering for current team size.

4. **Path Forward**: Option 2 is a subset of Option 1. We're not closing doors.

5. **Immediate Value**: Value objects like `Money` solve real bugs (currency mismatches) today.

## Consequences

### Positive

- **Better Testing**: Repository interfaces allow mocking database in unit tests
- **Clearer Intent**: Value objects make code self-documenting (`Money` vs `float`)
- **Reduced Bugs**: Centralized currency handling prevents conversion errors
- **Incremental Path**: Can expand to full Clean Architecture if needed
- **Low Risk**: Small, targeted changes are easier to validate

### Negative

- **Mixed Patterns**: Some services use new pattern, others use old
- **Learning Curve**: Need to understand when to use which pattern
- **Partial Coupling**: ORM coupling remains in non-refactored services
- **Documentation Needed**: Must document which pattern applies where

### Risks and Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Inconsistent codebase | Medium | Medium | Document patterns, refactor in waves |
| Over-abstracting simple operations | Medium | Low | Only abstract where tests are needed |
| Breaking existing functionality | Low | High | Comprehensive test coverage before refactoring |
| Scope creep during refactoring | Medium | Medium | Strict phase boundaries, PR per phase |

## Implementation Plan

### Phase 1: Value Objects (Week 1)
- [ ] Create `domain/value_objects/money.py`
- [ ] Create `domain/value_objects/ticker.py`
- [ ] Refactor `CurrencyService` to use `Money`
- [ ] Add unit tests for value objects

### Phase 2: Repository Interfaces (Week 2)
- [ ] Create `domain/interfaces/holding_repository.py`
- [ ] Create `adapters/repositories/sqlalchemy_holding_repo.py`
- [ ] Refactor one router to use repository
- [ ] Demonstrate unit test without database

### Phase 3: First Use Case (Week 3)
- [ ] Convert `PortfolioReconstructionService` to Use Case pattern
- [ ] Extract domain entity for `Holding` (pure Python, no ORM)
- [ ] Add comprehensive tests
- [ ] Document pattern for future use

### Phase 4: Evaluate (Week 4)
- [ ] Review implementation quality
- [ ] Gather lessons learned
- [ ] Decide: expand to more services or pause
- [ ] Update this ADR with learnings

## Alternatives Not Chosen

### Why Not Full Clean Architecture Now?

The full pattern requires:
- Separate ORM models from domain entities (14 models to duplicate)
- Mappers between ORM and domain (boilerplate)
- Interfaces for all external dependencies
- Use cases for all operations

For a solo project, this risks:
- Analysis paralysis
- Boilerplate fatigue
- Over-abstraction of simple CRUD

The lightweight approach tests the waters first.

### Why Not Just Reorganize Folders?

Folder reorganization improves navigation but doesn't address:
- ORM coupling in business logic
- Difficulty testing without database
- Currency handling scattered across services

These are the actual pain points.

## Related Decisions

- Future: ADR-0002 may address Event Sourcing for transaction history
- Future: ADR-0003 may address API versioning strategy

## References

- [Clean Architecture by Robert C. Martin](https://blog.cleancoder.com/uncle-bob/2012/08/13/the-clean-architecture.html)
- [Hexagonal Architecture by Alistair Cockburn](https://alistair.cockburn.us/hexagonal-architecture/)
- Current architecture: `docs/ARCHITECTURE.md`

## Review Checklist

- [x] Context clearly explains the problem
- [x] All viable options considered
- [x] Pros/cons balanced and honest
- [x] Consequences (positive and negative) documented
- [x] Implementation plan is realistic
- [ ] Stakeholder review (pending)
