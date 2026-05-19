# sutmaster

`sutmaster` è una libreria Python per gestire il ciclo di vita dei SUT in modalità `docker-compose` e `systemctl` con flusso di copia file via SSH.

## Configurazione

La libreria legge i SUT dal file `sut-config.yaml`.
Se vuoi usare un file diverso senza passarlo esplicitamente, puoi impostare la variabile d'ambiente `SUTMASTER_YAML`.

- `type`: `docker-compose` o `systemctl`
- `ssh`: host/port/username/private_key/password/password_env
- `copy_files`: lista `src`/`dest` da copiare via SSH
- `post_copy_commands`: comandi da eseguire dopo la copia

`password_env` permette di leggere la password SSH da una variabile d'ambiente (consigliato rispetto a scriverla in chiaro).

### Chiavi Docker Compose

- `path_to_compose`: path del file compose
- `container_name`: container target per `docker cp`
- `override_entrypoint`: se `true` avvia i container con entrypoint sostituito
- `entrypoint_command`: comando di override (es. `sleep infinity`)

Flusso Docker Compose:
1. `docker compose up -d` (con override opzionale)
2. copia file/cartelle nel container
3. esecuzione `post_copy_commands` (es. avvio app)

### Chiavi Systemd

- `service_name`: nome del servizio

Flusso Systemd:
1. copia file/cartelle su host remoto via SSH
2. esecuzione `post_copy_commands`
3. `systemctl start <service_name>`

## Robot Framework

Esempio in `tests/example.robot` con i keyword:

- `Start Sut`
- `Stop Sut`
- `Status Sut`
