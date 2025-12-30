# Fixtures

Chaque cas de test doit être placé dans un dossier `fixtures/<CASE_ID>/` avec la structure suivante :

```
fixtures/<CASE_ID>/
  source.pdf       # devis PDF de référence
  expected.json    # dictionnaire attendu pour le parser
```

`expected.json` doit au minimum contenir les clés utilisées dans les tests :
`devis_full`, `ref_affaire`, `client_nom`, `commercial_nom`, `fourniture_ht`, `prestations_ht`, `pose_sold`.

Pour ajouter un nouveau cas :
1. Créez un dossier `fixtures/<NOUVEL_ID>`.
2. Ajoutez `source.pdf` qui représente un devis RIAUX.
3. Ajoutez `expected.json` aligné sur les valeurs attendues.
4. Mettez à jour les tests si de nouvelles clés sont nécessaires.
