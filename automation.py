import os
import yaml
import logging
from datetime import datetime
from netmiko import ConnectHandler, SSHDetect, NetmikoTimeoutException, NetmikoAuthenticationException

# Configuration du logging
logging.basicConfig(
    filename='logs/deployment.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def load_inventory(filepath="inventory.yml"):
    with open(filepath, "r") as f:
        return yaml.safe_load(f)["devices"]

def get_role_from_prompt(prompt):
    hostname = prompt.rstrip("#>").strip()
    if hostname.startswith("R"):
        return "routeur", hostname
    elif "CORE" in hostname:
        return "core", hostname
    elif "ACC" in hostname:
        return "acces", hostname
    return "inconnu", hostname

def load_config_commands(hostname):
    """
    Charge le fichier de configuration et nettoie les commandes 
    incompatibles avec netmiko.send_config_set()
    """
    path = f"configs/{hostname}.txt"
    if not os.path.exists(path):
        raise FileNotFoundError(f"Fichier de configuration introuvable : {path}")
    
    clean_commands = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            cmd = line.strip()
            # Filtre les lignes vides, les commentaires (# ou !)
            if not cmd or cmd.startswith("#") or cmd.startswith("!"):
                continue
            # Netmiko gère déjà 'configure terminal' et 'end' / 'exit'
            if cmd.lower() in ["configure terminal", "conf t", "end", "exit"]:
                continue
            clean_commands.append(cmd)
            
    return clean_commands

def save_config_safely(net, device_type, hostname):
    """
    Sauvegarde la configuration en NVRAM en évitant le piège du prompt
    interactif de 'copy running-config startup-config' sur IOS
    ('Destination filename [startup-config]?'), qui bloque
    net.save_config() par défaut (confirm=False) et provoque une
    erreur 'Search pattern never detected in send_command'.
    """
    if device_type in ("cisco_ios", "cisco_xe"):
        # 'write memory' n'a pas de prompt de confirmation sur IOS/IOS-XE
        net.save_config(cmd="write memory")
    else:
        # Pour les autres plateformes (NX-OS, etc.), on confirme explicitement
        net.save_config(confirm=True)
    print(f"   Sauvegarde NVRAM effectuée sur {hostname}.")

def deploy():
    os.makedirs("backups", exist_ok=True)
    os.makedirs("logs", exist_ok=True)
    devices = load_inventory()

    for dev in devices:
        ip = dev["host"]
        print(f"\n Connexion vers {ip}...")
        try:
            # 1. Autodétection du type OS avec SSHDetect
            guesser = SSHDetect(**dev)
            dev["device_type"] = guesser.autodetect()
            print(f"   OS détecté : {dev['device_type']}")

            with ConnectHandler(**dev) as net:
                net.enable()
                
                # 2. Identification dynamique via le prompt
                prompt = net.find_prompt()
                role, hostname = get_role_from_prompt(prompt)
                print(f"   Équipement : {hostname} | Rôle : {role}")

                # 3. Sauvegarde pré-déploiement
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                backup_filename = f"backups/{hostname}_{timestamp}.cfg"
                running_config = net.send_command("show running-config")
                with open(backup_filename, "w", encoding="utf-8") as bf:
                    bf.write(running_config)
                print(f"   Backup sauvegardé : {backup_filename}")

                # 4. Application des configurations
                commands = load_config_commands(hostname)
                if commands:
                    output = net.send_config_set(commands)
                    print(f"   Configuration appliquée avec succès sur {hostname}.")
                else:
                    print(f"   Aucune commande à appliquer pour {hostname}.")
                
                # 5. Écriture en NVRAM (copy running-config startup-config)
                save_config_safely(net, dev["device_type"], hostname)
                logging.info(f"Déploiement réussi sur {hostname} ({ip})")

        except NetmikoAuthenticationException:
            err = f"Échec d'authentification sur {ip}"
            print(f"   {err}")
            logging.error(err)
        except NetmikoTimeoutException:
            err = f"Timeout / Équipement injoignable : {ip}"
            print(f"   {err}")
            logging.error(err)
        except Exception as e:
            err = f"Erreur sur {ip} : {str(e)}"
            print(f"   {err}")
            logging.error(err)

if __name__ == "__main__":
    deploy()
