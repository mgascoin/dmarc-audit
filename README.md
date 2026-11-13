# dmarc-audit

Petit outil en Python pour vérifier en masse la configuration **DMARC** d'une liste de domaines.

Il classe chaque domaine dans l'une de ces catégories :

| Catégorie | Signification |
|---|---|
| `aucun DMARC` | Aucun enregistrement publié : le domaine est usurpable, et ses emails sont exposés aux rejets de certaines messageries |
| `p=none` | DMARC en mode surveillance : les emails passent, mais rien n'empêche l'usurpation du domaine |
| `p=quarantine` | Les emails non authentifiés sont envoyés en spam |
| `p=reject` | Les emails non authentifiés sont refusés : c'est la protection maximale |
| `invalide` | Enregistrement mal formé, ou plusieurs enregistrements publiés (le DMARC est alors ignoré) |
| `erreur DNS` | Timeout ou erreur du serveur DNS |

Il signale aussi deux points faibles fréquents :
- un DMARC **sans adresse de rapports** (`rua` absent) : le propriétaire ne voit pas qui envoie des emails en son nom ;
- un DMARC **appliqué partiellement** (`pct` < 100).

## Pourquoi c'est important

Depuis 2024, Gmail et Yahoo exigent SPF, DKIM et DMARC de la part des gros expéditeurs. Microsoft a suivi en mai 2025 pour Outlook.com. Depuis le 5 novembre 2026, des rejets sont signalés sur Outlook.com, Hotmail, Live et MSN pour des domaines **sans enregistrement DMARC**, quel que soit leur volume d'envoi :

```
550 5.7.1 Message rejected: Message lacks SPF/DKIM/DMARC Auth Records
```

Pour un site e-commerce, ça peut vouloir dire des confirmations de commande ou des réinitialisations de mot de passe qui n'arrivent jamais.

## Une vérification non intrusive

Un enregistrement DMARC est un enregistrement DNS TXT **public**, publié à l'adresse `_dmarc.<domaine>`. Tous les serveurs de messagerie le lisent pour décider quoi faire des emails qu'ils reçoivent.

L'outil se contente de **lire cet enregistrement public**, comme le ferait n'importe quel serveur mail. Il n'envoie aucun email, ne teste aucune vulnérabilité et ne contacte pas les serveurs des domaines audités.

## Installation

Python 3.8 ou plus récent.

```bash
git clone https://github.com/mgascoin/dmarc-audit.git
cd dmarc-audit
pip install -r requirements.txt
```

## Utilisation

1. Créez un fichier `domaines.txt` avec un domaine par ligne :

```
# Les lignes commençant par # sont ignorées
exemple-boutique.fr
https://www.autre-site.com/
troisieme-domaine.fr
```

Les préfixes `http(s)://`, `www.` et les chemins d'URL sont retirés automatiquement, et les doublons sont supprimés.

2. Lancez l'audit :

```bash
python3 audit_dmarc.py domaines.txt
```

3. Exemple de sortie (domaines et chiffres fictifs) :

```
[  1/3] exemple-boutique.fr                 p=none
[  2/3] autre-site.com                      aucun DMARC
[  3/3] troisieme-domaine.fr                p=reject

===== Résumé =====
aucun DMARC       1  (33 %)
p=none            1  (33 %)
p=quarantine      0  (0 %)
p=reject          1  (33 %)

DMARC sans rapports (rua absent) : 0
DMARC appliqué partiellement (pct < 100) : 0

Détail : resultats_dmarc.csv
```

Le fichier `resultats_dmarc.csv` contient le détail de chaque domaine : catégorie, valeurs de `p`, `sp`, `pct` et `rua`, et l'enregistrement complet.

## Votre domaine n'a pas de DMARC ?

Commencez en mode surveillance pour recevoir les rapports sans rien bloquer :

```
_dmarc.votredomaine.fr.  TXT  "v=DMARC1; p=none; rua=mailto:dmarc@votredomaine.fr"
```

Analysez ensuite les rapports pour identifier tous vos services d'envoi légitimes (ESP, CRM, outil de facturation…). Une fois qu'ils passent tous SPF ou DKIM avec un domaine aligné, montez progressivement vers `p=quarantine`, puis `p=reject`.

## Limites

- L'outil interroge directement `_dmarc.<domaine>` et ne remonte pas au domaine organisationnel pour les sous-domaines. Pour un sous-domaine sans enregistrement propre, la politique du domaine parent (via `sp=` ou `p=`) peut quand même s'appliquer.
- Il vérifie la **présence et la politique** du DMARC, pas l'alignement réel des emails envoyés. Pour ça, il faut regarder les rapports DMARC ou les en-têtes `Authentication-Results` d'un email reçu.

## Licence

[MIT](LICENSE)
