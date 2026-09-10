# Example EXPLAIN plans

Recorded read-only against the live graph. Extra property indexes are **not** added unless a plan shows a hot LabelScan that listing limits cannot contain.

Fingerprint: `{'pokemon_count': 1351, 'encounter_count': 111515, 'learnset_entry_count': 638321, 'game_version_count': 41, 'version_group_count': 28, 'latest_learnset_retrieved_at': '2026-08-30T12:04:57.927956+00:00'}`

## `discovery/dataset_fingerprint.cypher`

```
ProduceResults@neo4j estimated_rows=1.0
  CartesianProduct@neo4j estimated_rows=1.0
    CartesianProduct@neo4j estimated_rows=1.0
      CartesianProduct@neo4j estimated_rows=1.0
        CartesianProduct@neo4j estimated_rows=1.0
          NodeCountFromCountStore@neo4j estimated_rows=1.0
          NodeCountFromCountStore@neo4j estimated_rows=1.0
        EagerAggregation@neo4j estimated_rows=1.0
          NodeByLabelScan@neo4j estimated_rows=638321.0
      NodeCountFromCountStore@neo4j estimated_rows=1.0
    NodeCountFromCountStore@neo4j estimated_rows=1.0
```

## `discovery/list_versions_with_data.cypher`

```
ProduceResults@neo4j estimated_rows=75.0
  Projection@neo4j estimated_rows=75.0
    CacheProperties@neo4j estimated_rows=75.0
      Skip@neo4j estimated_rows=75.0
        Top@neo4j estimated_rows=76.0
          Projection@neo4j estimated_rows=275.4993591190368
            Filter@neo4j estimated_rows=275.4993591190368
              OrderedAggregation@neo4j estimated_rows=333.938617113984
                OptionalExpand(All)@neo4j estimated_rows=111515.0
                  OptionalExpand(All)@neo4j estimated_rows=41.0
                    NodeByLabelScan@neo4j estimated_rows=41.0
```

## `discovery/list_version_groups_with_data.cypher`

```
ProduceResults@neo4j estimated_rows=27.265702465237
  Projection@neo4j estimated_rows=27.265702465237
    Skip@neo4j estimated_rows=27.265702465237
      Top@neo4j estimated_rows=28.265702465237
        Projection@neo4j estimated_rows=28.265702465237
          EagerAggregation@neo4j estimated_rows=28.265702465237
            Sort@neo4j estimated_rows=798.9499358533049
              Projection@neo4j estimated_rows=798.9499358533049
                OptionalExpand(All)@neo4j estimated_rows=798.9499358533049
                  OrderedAggregation@neo4j estimated_rows=798.9499358533049
                    Filter@neo4j estimated_rows=638321.0
                      Expand(All)@neo4j estimated_rows=638362.0
                        NodeByLabelScan@neo4j estimated_rows=28.0
```

## `discovery/resolve_version_group.cypher`

```
ProduceResults@neo4j estimated_rows=0.7589285714285713
  Projection@neo4j estimated_rows=0.7589285714285713
    Filter@neo4j estimated_rows=0.7589285714285713
      Expand(All)@neo4j estimated_rows=0.9999999999999999
        NodeUniqueIndexSeek@neo4j estimated_rows=0.9999999999999999
```

## `discovery/find_pokemon_by_name.cypher`

```
ProduceResults@neo4j estimated_rows=75.0
  Projection@neo4j estimated_rows=75.0
    Skip@neo4j estimated_rows=75.0
      Limit@neo4j estimated_rows=76.0
        OptionalExpand(All)@neo4j estimated_rows=76.0
          Sort@neo4j estimated_rows=76.0
            Projection@neo4j estimated_rows=854.9296875
              Filter@neo4j estimated_rows=854.9296875
                NodeByLabelScan@neo4j estimated_rows=1351.0
```

## `encounters/pokemon_in_area.cypher`

```
ProduceResults@neo4j estimated_rows=0.03457411732136273
  Projection@neo4j estimated_rows=0.03457411732136273
    CacheProperties@neo4j estimated_rows=0.03457411732136273
      Skip@neo4j estimated_rows=0.03457411732136273
        Top@neo4j estimated_rows=1.0345741173213627
          Projection@neo4j estimated_rows=1.0345741173213627
            OptionalExpand(All)@neo4j estimated_rows=1.0345741173213627
              OptionalExpand(All)@neo4j estimated_rows=1.0345741173213627
                Filter@neo4j estimated_rows=1.0345741173213627
                  Expand(All)@neo4j estimated_rows=1.0345741173213627
                    Filter@neo4j estimated_rows=1.0345741173213627
                      Expand(All)@neo4j estimated_rows=1.3722848395557974
                        Filter@neo4j estimated_rows=1.3722848395557974
                          Expand(All)@neo4j estimated_rows=56.263678421787695
                            Filter@neo4j estimated_rows=56.263678421787695
                              Expand(All)@neo4j estimated_rows=77.87360335195531
                                NodeUniqueIndexSeek@neo4j estimated_rows=1.0
```

## `encounters/locations_of_pokemon.cypher`

```
ProduceResults@neo4j estimated_rows=0.09660261732360587
  Projection@neo4j estimated_rows=0.09660261732360587
    CacheProperties@neo4j estimated_rows=0.09660261732360587
      Skip@neo4j estimated_rows=0.09660261732360587
        PartialTop@neo4j estimated_rows=1.0966026173236059
          Projection@neo4j estimated_rows=1.0966026173236059
            OptionalExpand(All)@neo4j estimated_rows=1.0966026173236059
              OptionalExpand(All)@neo4j estimated_rows=1.0966026173236059
                Filter@neo4j estimated_rows=1.0966026173236059
                  Expand(All)@neo4j estimated_rows=1.0966026173236059
                    Filter@neo4j estimated_rows=1.0966026173236059
                      Expand(All)@neo4j estimated_rows=1.4545609846364926
                        Filter@neo4j estimated_rows=1.4545609846364926
                          Expand(All)@neo4j estimated_rows=59.63700037009619
                            Filter@neo4j estimated_rows=59.63700037009619
                              Expand(All)@neo4j estimated_rows=82.54256106587711
                                NodeUniqueIndexSeek@neo4j estimated_rows=0.9999999999999998
```

## `encounters/compare_versions.cypher`

```
ProduceResults@neo4j estimated_rows=62.46415896079426
  Skip@neo4j estimated_rows=62.46415896079426
    Top@neo4j estimated_rows=63.46415896079426
      Projection@neo4j estimated_rows=63.46415896079426
        Projection@neo4j estimated_rows=63.46415896079426
          EagerAggregation@neo4j estimated_rows=63.46415896079426
            CacheProperties@neo4j estimated_rows=4027.6994726009625
              Filter@neo4j estimated_rows=4027.6994726009625
                Expand(All)@neo4j estimated_rows=4027.6994726009625
                  SelectOrSemiApply@neo4j estimated_rows=5370.015634771732
                    Filter@neo4j estimated_rows=5370.015634771732
                      Expand(All)@neo4j estimated_rows=5370.015634771732
                        NodeUniqueIndexSeek@neo4j estimated_rows=1.9743589743589742
                    Limit@neo4j estimated_rows=5370.015634771732
                      Filter@neo4j estimated_rows=3.7500109181366845
                        Expand(All)@neo4j estimated_rows=5370.015634771732
                          Argument@neo4j estimated_rows=5370.015634771732
```

## `learnsets/learnset_for_pokemon.cypher`

```
ProduceResults@neo4j estimated_rows=11.69791034418949
  Projection@neo4j estimated_rows=11.69791034418949
    CacheProperties@neo4j estimated_rows=11.69791034418949
      Skip@neo4j estimated_rows=11.69791034418949
        Top@neo4j estimated_rows=12.69791034418949
          Projection@neo4j estimated_rows=12.69791034418949
            CacheProperties@neo4j estimated_rows=12.69791034418949
              Filter@neo4j estimated_rows=12.69791034418949
                Expand(All)@neo4j estimated_rows=12.69791034418949
                  Filter@neo4j estimated_rows=12.69791034418949
                    Expand(All)@neo4j estimated_rows=16.874299460716927
                      Filter@neo4j estimated_rows=16.874299460716927
                        Expand(All)@neo4j estimated_rows=472.480384900074
                          Filter@neo4j estimated_rows=472.480384900074
                            Expand(All)@neo4j estimated_rows=472.480384900074
                              CacheProperties@neo4j estimated_rows=1.0
                                NodeUniqueIndexSeek@neo4j estimated_rows=1.0
```

## `learnsets/who_learns_move.cypher`

```
ProduceResults@neo4j estimated_rows=19.594089885954382
  Projection@neo4j estimated_rows=19.594089885954382
    CacheProperties@neo4j estimated_rows=19.594089885954382
      Skip@neo4j estimated_rows=19.594089885954382
        Top@neo4j estimated_rows=20.594089885954382
          Projection@neo4j estimated_rows=20.594089885954382
            CacheProperties@neo4j estimated_rows=20.594089885954382
              Filter@neo4j estimated_rows=20.594089885954382
                Expand(All)@neo4j estimated_rows=20.594089885954382
                  Filter@neo4j estimated_rows=20.594089885954382
                    Expand(All)@neo4j estimated_rows=27.367561310238383
                      Filter@neo4j estimated_rows=27.367561310238383
                        Expand(All)@neo4j estimated_rows=766.2917166866747
                          Filter@neo4j estimated_rows=766.2917166866747
                            Expand(All)@neo4j estimated_rows=766.2917166866747
                              CacheProperties@neo4j estimated_rows=1.0000000000000002
                                NodeUniqueIndexSeek@neo4j estimated_rows=1.0000000000000002
```

## `evolutions/evolutions_from_species.cypher`

```
ProduceResults@neo4j estimated_rows=0.0
  Projection@neo4j estimated_rows=0.0
    CacheProperties@neo4j estimated_rows=0.0
      Skip@neo4j estimated_rows=0.0
        Top@neo4j estimated_rows=0.5336585365853659
          Projection@neo4j estimated_rows=0.5336585365853659
            Projection@neo4j estimated_rows=0.5336585365853659
              EagerAggregation@neo4j estimated_rows=0.5336585365853659
                OptionalExpand(All)@neo4j estimated_rows=0.5336585365853659
                  Filter@neo4j estimated_rows=0.5336585365853659
                    Expand(All)@neo4j estimated_rows=0.5336585365853659
                      NodeUniqueIndexSeek@neo4j estimated_rows=1.0
```

## `evolutions/evolution_chain.cypher`

```
ProduceResults@neo4j estimated_rows=0.0055299960781574065
  Projection@neo4j estimated_rows=0.0055299960781574065
    CacheProperties@neo4j estimated_rows=0.0055299960781574065
      Skip@neo4j estimated_rows=0.0055299960781574065
        Top@neo4j estimated_rows=1.0055299960781574
          Projection@neo4j estimated_rows=1.0055299960781574
            Projection@neo4j estimated_rows=1.0055299960781574
              EagerAggregation@neo4j estimated_rows=1.0055299960781574
                OptionalExpand(All)@neo4j estimated_rows=1.0110905730129391
                  Filter@neo4j estimated_rows=1.0110905730129391
                    Expand(All)@neo4j estimated_rows=1.0110905730129391
                      Filter@neo4j estimated_rows=1.8946395563770797
                        Expand(All)@neo4j estimated_rows=1.8946395563770797
                          Filter@neo4j estimated_rows=1.0
                            Expand(All)@neo4j estimated_rows=1.0
                              NodeUniqueIndexSeek@neo4j estimated_rows=1.0
```

## `matchups/type_effectiveness.cypher`

```
ProduceResults@neo4j estimated_rows=1.2514979921191691
  Projection@neo4j estimated_rows=1.2514979921191691
    Sort@neo4j estimated_rows=1.2514979921191691
      Projection@neo4j estimated_rows=1.2514979921191691
        Projection@neo4j estimated_rows=1.2514979921191691
          Projection@neo4j estimated_rows=1.2514979921191691
            EagerAggregation@neo4j estimated_rows=1.2514979921191691
              Projection@neo4j estimated_rows=1.5662472242783119
                OptionalExpand(Into)@neo4j estimated_rows=1.5662472242783119
                  Projection@neo4j estimated_rows=1.5662472242783119
                    CartesianProduct@neo4j estimated_rows=1.5662472242783119
                      NodeUniqueIndexSeek@neo4j estimated_rows=1.0
                      Filter@neo4j estimated_rows=1.566247224278312
                        Expand(All)@neo4j estimated_rows=1.566247224278312
                          NodeUniqueIndexSeek@neo4j estimated_rows=0.9999999999999998
```

## `matchups/offensive_coverage_by_types.cypher`

```
ProduceResults@neo4j estimated_rows=0.5662472242783119
  Projection@neo4j estimated_rows=0.5662472242783119
    CacheProperties@neo4j estimated_rows=0.5662472242783119
      Skip@neo4j estimated_rows=0.5662472242783119
        Top@neo4j estimated_rows=1.5662472242783119
          Projection@neo4j estimated_rows=1.5662472242783119
            Projection@neo4j estimated_rows=1.5662472242783119
              Projection@neo4j estimated_rows=1.5662472242783119
                EagerAggregation@neo4j estimated_rows=1.5662472242783119
                  Projection@neo4j estimated_rows=2.453130367559517
                    OptionalExpand(Into)@neo4j estimated_rows=2.453130367559517
                      Projection@neo4j estimated_rows=2.453130367559517
                        CartesianProduct@neo4j estimated_rows=2.453130367559517
                          Filter@neo4j estimated_rows=1.566247224278312
                            Expand(All)@neo4j estimated_rows=1.566247224278312
                              NodeUniqueIndexSeek@neo4j estimated_rows=0.9999999999999998
                          Filter@neo4j estimated_rows=1.566247224278312
                            Expand(All)@neo4j estimated_rows=1.566247224278312
                              NodeUniqueIndexSeek@neo4j estimated_rows=0.9999999999999998
```

## `matchups/offensive_coverage_by_learnset.cypher`

```
ProduceResults@neo4j estimated_rows=3.4596038871991377
  Projection@neo4j estimated_rows=3.4596038871991377
    CacheProperties@neo4j estimated_rows=3.4596038871991377
      Skip@neo4j estimated_rows=3.4596038871991377
        Top@neo4j estimated_rows=4.459603887199138
          Projection@neo4j estimated_rows=4.459603887199138
            CacheProperties@neo4j estimated_rows=4.459603887199138
              Projection@neo4j estimated_rows=4.459603887199138
                Projection@neo4j estimated_rows=4.459603887199138
                  EagerAggregation@neo4j estimated_rows=4.459603887199138
                    Projection@neo4j estimated_rows=19.88806683072166
                      OptionalExpand(Into)@neo4j estimated_rows=19.88806683072166
                        Projection@neo4j estimated_rows=19.88806683072166
                          Filter@neo4j estimated_rows=19.88806683072166
                            Expand(All)@neo4j estimated_rows=19.88806683072166
                              Apply@neo4j estimated_rows=12.69791034418949
                                Projection@neo4j estimated_rows=12.69791034418949
                                  OptionalExpand(All)@neo4j estimated_rows=12.69791034418949
                                    Apply@neo4j estimated_rows=12.69791034418949
                                      CacheProperties@neo4j estimated_rows=12.69791034418949
                                        Filter@neo4j estimated_rows=12.69791034418949
                                          Expand(All)@neo4j estimated_rows=12.69791034418949
                                            Filter@neo4j estimated_rows=12.69791034418949
                                              Expand(All)@neo4j estimated_rows=16.874299460716927
                                                Filter@neo4j estimated_rows=16.874299460716927
                                                  Expand(All)@neo4j estimated_rows=472.480384900074
                                                    Filter@neo4j estimated_rows=472.480384900074
                                                      Expand(All)@neo4j estimated_rows=472.480384900074
                                                        NodeUniqueIndexSeek@neo4j estimated_rows=1.0
                                      Optional@neo4j estimated_rows=12.69791034418949
                                        Filter@neo4j estimated_rows=11.42811930977054
                                          NodeByLabelScan@neo4j estimated_rows=228.56238619541082
                                NodeUniqueIndexSeek@neo4j estimated_rows=12.69791034418949
```

## Index decision

No additional indexes were added from this pass. Identity lookups use existing uniqueness constraints. Name discovery may LabelScan; add a `name` index only if agent traffic makes that scan expensive.
