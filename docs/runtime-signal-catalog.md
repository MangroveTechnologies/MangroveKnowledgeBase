# Runtime signal catalog contract

`RuleRegistry.names()` and `catalog()` contain exactly the canonical registered identities. Retired aliases do not inflate that set. `describe(name)` resolves an alias while retaining the requested `rule_name` and the canonical identity; an unknown name returns an empty dictionary.

The runtime registry decides existence. The ontology may intentionally exclude a signal without making it unknown. Consumers enrich descriptors with `modelled` and graph descriptions instead of using graph membership as an execution allowlist.

Descriptors separate eligibility from compatibility:

- `active`: current signal; eligible for new composition and execution.
- `deprecated`: a retired spelling or deprecated implementation. It remains known and executable unless explicitly disabled; the reason explains its replacement.
- `disabled`: excluded from new composition. `composable` is false. Existing deprecated disabled signals retained by KB141, including ATRTrailingStop signals, remain `executable=true` and `legacy_compatible=true` for stored strategies.
- `register(name, executable=False)` is an explicit runtime prohibition. It sets `executable=false` and cannot be overridden by deprecation or aliases. The registered callable rejects before invoking the implementation.

A disabled docstring on a non-deprecated signal prevents execution as well as composition. This does not reclassify the deprecated compatibility entries. Never interpret the status label alone as the execution decision: use `composable` for new selections and `executable` for stored execution. Display `reason` when explaining an exclusion.

Consumers must install the reviewed companion commit before calling `describe` or `catalog`; these APIs do not exist in the older 3.4.0 wheel. No package release or production activation is part of this change.
