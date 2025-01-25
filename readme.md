# Qui vote quoi ?

### *Surveillez les votes des députés européens français*

Ce projet vise à faciliter l'accès aux données du parlement européen relatives aux votes. Il vous permet de facilement retrouver tous les textes de loi votés contenant certains mots clés.

### [https://qui-vote-quoi.fr](https://qui-vote-quoi.fr)

## Pourquoi ce projet ?

Le site web du parlement européen est peu ergonomique et ne permet pas de rechercher les résultats des votes à partir de mots clés. Or, ce type de recherche est essentiel pour s'assurer que les élus respectent leurs promesses électorales.

## Limites

> [!WARNING]  
> Les données utilisées dans ce projet proviennent de europarl.europa.eu qui ne fournit pas d'API pour récupérer les données relatives aux votes. Elles ont été extraites à partir du HTML retourné par certaines requêtes. Il est donc envisageable que ce site contienne des erreurs. N'hésitez pas à vérifier les données en cliquant sur les sources dans le détail des votes.
>
> Ce site n'est aucunement affilié au parlement européen et n'est pas officiel.

Les données des votes par pays ne sont disponibles que depuis la mandature de 2019. Ainsi, ce site ne posède aucune donnée concernant les votes antérieurs à cette mandature.

Si plusieurs votes ont eu lieu pour un même document (par exemple `RC-B-10-0035-2024`), le seul qui est affiché correspond au dernier de la liste sur le site de europarl. En pratique, cela correspond presque toujours à la proposition de résolution associée à ce document. Les votes au détail par amendement ne sont pas disponibles.

## Contact

Pour signaler un problème, merci d'utiliser les [issues GitHub](https://github.com/Teskann/qui-vote-quoi/issues).

Pour toute prise de contact, vous pouvez m'écrire à `teskann-dev@protonmail.com`.

## Debug (Linux)

```bash
python -mvenv .venv
source ./.venv/bin/activate
pip install -r requirements.txt
```

Pour lancer le serveur localement, créez un fichier `database_path.txt` à la racine du projet.
Il doit contenir le chemin vers la base de données des résultats des votes. Par exemple:
```text
/home/user/database-qui-vote-quoi
```
Sans cela, vous aurez une erreur au lancement de l'application:

```bash
echo /home/user/database-qui-vote-quoi >> database_path.txt
```

```bash
python app.py  # Lance le serveur en debug
```
## Extraire la base de données de europarl.europa.eu

Lancez dans l'environnement virtuel python:
```bash
python fill_database.py -h
```
Pour savoir comment récupérer la base de données.

## Mise à jour automatique de la base de données quotidiennement

Pour la mise à jour automatique de votre base de données, vous pouvez lancer
```bash
python fill_database_from.py today  # Récupère les données des votes d'aujourd'hui
python fill_database_from.py yesterday  # Récupère les données des votes d'hier
```

Vous pouvez ajouter le lancement de ce script à crontab pour que cela se fasse automatiquement:

- Créez un fichier `update.sh` n'importe où sur votre disque, disons `/home/user`
```bash
#!/bin/bash
cd /home/user/qui-vote-quoi
source ./.venv/bin/activate
python fill_database_from.py yesterday
# python fill_database_from.py today 
deactivate
cd -
```

- Puis, lancez `crontab -e` et ajoutez ceci:

```cron
0 1 * * * /home/user/update.sh
```