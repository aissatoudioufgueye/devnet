# Projet DevNet — Automatisation réseau campus multi-sites

Automatisation complète du lab Groupe-ISI (Dakar / Abidjan) : détection
automatique du type d'équipement et de son rôle, backup horodaté,
migration OSPF → EIGRP, activation du Spanning Tree portfast sur les
ports d'accès, et sauvegarde de la configuration.

## Structure

```
├── automation.py       # script principal (connexion, autodetect, push, backup, save)
├── inventory.yaml       # inventaire des équipements (host uniquement, pas de secret)
├── configs/              # une config .txt par équipement (nom = hostname)
├── tests/                 # test pytest sur detect_role() (fonction pure)
├── logs/                   # généré à l'exécution (horodaté), ignoré par git
├── backups/                # running-config sauvegardés avant modification, ignoré par git
├── .env.example             # variables d'environnement attendues (à copier en .env)
└── requirements.txt
```

## Installation

1. Créer un environnement virtuel et installer les dépendances :

   ```bash
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

2. Copier `.env.example` vers `.env` et renseigner vos identifiants :

   ```bash
   cp .env.example .env
   # puis éditer .env avec votre éditeur habituel
   ```

   `.env` est ignoré par Git : aucun secret n'est jamais versionné.

3. Vérifier/adapter `inventory.yaml` si votre lab a des adresses de
   management différentes, et les fichiers `configs/<hostname>.txt` si
   vous changez le plan d'adressage.

## Exécution

Sur un lab fraîchement réinitialisé (configuration de management
uniquement) :

```bash
python automation.py
```

Le script, pour chaque équipement de `inventory.yaml` :
1. détecte automatiquement le type d'OS (SSHDetect) ;
2. se connecte et identifie le rôle réel via le hostname (`find_prompt`) ;
3. sauvegarde le running-config actuel dans `backups/` ;
4. applique la configuration `configs/<hostname>.txt` (retrait OSPF,
   ajout EIGRP côté routeurs ; VLAN/trunk/portfast côté switchs) ;
5. sauvegarde la configuration (`write memory`).

Un échec sur un équipement (auth, timeout, config invalide...) est
journalisé et n'interrompt pas le traitement des suivants. Le bilan
final (succès/échecs) s'affiche en console et dans `logs/run_<date>.log`.

Critère de réussite minimal : après exécution, PC1 doit pouvoir pinguer
PC2.

## Tests

```bash
pytest tests/
```

## Extension bonus : 3e site (Saint-Louis)

Le lab compte désormais un 3e site (`R3-SL`, `SW5-CORE`, `SW6-ACC`),
raccordé en étoile depuis `R1-DKR` (nouveau lien `192.168.30.0/24`),
VLAN 30 en `10.30.10.0/24`.

Ajouté **uniquement** via `inventory.yaml` + 3 nouveaux fichiers dans
`configs/` : `automation.py` n'a nécessité aucune modification, ce qui
démontre la généricité de l'outil demandée au §2 du cahier des charges
(les tests `test_detect_role_*` couvrent aussi ces nouveaux hostnames).

Choix retenus pour cette extension (à ajuster si besoin) :
- **Routage** : EIGRP AS 100 étendu aux 3 sites (au lieu d'une
  cohabitation OSPF/EIGRP avec redistribution, plus complexe à
  justifier pour un gain limité).
- **Adressage** : garde la convention du socle obligatoire
  (`10.<site>0.10.0/24`) plutôt qu'un schéma alternatif, conformément
  au §9 qui déconseille de redéfinir l'adressage.
- **Pare-feu / DMZ / sortie Internet** : non automatisés — hors
  périmètre du cahier des charges actuel.

## Limites connues

- Le nom du fichier de config à pousser est déduit du hostname renvoyé
  par l'équipement ; un hostname personnalisé hors convention
  `R*-*` / `*CORE*` / `*ACC*` ne serait pas reconnu par `detect_role()`.
- Pas de rollback automatique en cas d'échec de `send_config_set` en
  cours d'exécution : seul le backup pré-modification permet de revenir
  en arrière manuellement.
