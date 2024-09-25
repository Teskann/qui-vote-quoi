# Qui vote quoi ?

### *Surveillez les votes des députés européens français*

Ce projet vise à faciliter l'accès aux données du parlement européen relatives aux votes. Il vous permet de facilement retrouver tous les textes de loi votés contenant certains mots clés.

*[Lien du site]("https://qui-vote-quoi.fr")*

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

Pour signaler un problème, merci d'utiliser les [issues GitHub](./issues).

Pour toute prise de contact, vous pouvez m'écrire à `teskann-dev@protonmail.com`.





