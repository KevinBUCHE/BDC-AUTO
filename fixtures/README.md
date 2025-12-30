# Fixtures

Ajoutez vos cas de test dans `fixtures/<CASE_ID>/` avec :

```
fixtures/<CASE_ID>/
  source.pdf       # devis PDF minimal contenant les ancres attendues
  expected.json    # valeurs attendues pour le parser
```

`expected.json` doit au minimum contenir : `devis_full`, `ref_affaire`, `client_nom`, `commercial_nom`, `fourniture_ht`, `prestations_ht`, `pose_sold`.
