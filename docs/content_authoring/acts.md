# Adding Acts

Acts are configured through manifest files under data/acts/.

Each act manifest defines:
- character class file
- card files
- enemy files
- encounter files
- status files
- event files
- relic files
- map settings
- treasure settings
- waiting room settings

Each act should have:
- at least one encounter file
- at least one event file
- a valid mimic encounter ID
- encounters whose act field matches the manifest act
- events whose act field matches the manifest act

The content integrity tests enforce these rules.
