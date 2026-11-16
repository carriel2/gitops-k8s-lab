# Weekly backup of the Sealed Secrets keys

The Sealed Secrets controller holds the private key that decrypts everything encrypted in Git. **Without that key the
`SealedSecret` objects in the repository are useless** (for example, if the cluster is rebuilt). This CronJob copies
the keys to S3 every week, **encrypted** with a public certificate of yours: whoever only has the S3 object reads nothing.

## How it works

One Pod, three steps, each in the image that has the right tool:

1. `read-keys` (kubectl): reads the Secrets labelled `sealedsecrets.bitnami.com/sealed-secrets-key` into an
   **in-memory** volume (gone with the Pod).
2. `encrypt` (openssl): encrypts with `backup.crt` (CMS, AES-256) and deletes the plaintext. The Pod only has the
   **public** certificate.
3. `upload` (aws cli): uploads the encrypted file to S3 and verifies the remote size. It only sees the encrypted file.

Permissions are minimal: a `Role` that can only read Secrets in the `sealed-secrets` namespace.

The object is written to `gitops-k8s-lab/sealed-keys/sealed-keys-YYYY-MM-DDTHHMMSSZ.cms`. Schedule: Saturday 22:30
(America/Sao_Paulo).

## Setup (once)

1. **Key pair (on your machine; the private key never goes to the cluster or to Git):**

   ```bash
   openssl req -x509 -newkey rsa:4096 -sha256 -days 3650 -nodes \
     -keyout sealed-backup.key -out sealed-backup.crt -subj "/CN=sealed-secrets-backup"
   ```

   Keep `sealed-backup.key` outside the server and outside S3 (a password manager, for example). Copy
   `sealed-backup.crt` into this folder as `backup.crt` and commit it: it is public.

2. **S3 credentials.** Create a Secret named `sealed-keys-backup-s3` with the keys `BACKUP_S3_ENDPOINT`,
   `BACKUP_S3_BUCKET`, `BACKUP_S3_ACCESS_KEY` and `BACKUP_S3_SECRET_KEY`, seal it with `kubeseal` for the
   `sealed-secrets` namespace, save the result here as `sealed-s3.yaml` and uncomment its line in `kustomization.yaml`:

   ```bash
   kubectl create secret generic sealed-keys-backup-s3 -n sealed-secrets \
     --from-env-file=s3.env --dry-run=client -o yaml \
     | kubeseal --controller-namespace sealed-secrets --format yaml > sealed-s3.yaml
   shred -u s3.env || rm -f s3.env
   ```

3. **Register the Application:** `kubectl apply -f argocd/sealed-keys-backup-app.yaml`

## Test it now

```bash
kubectl create job --from=cronjob/sealed-keys-backup test-backup-1 -n sealed-secrets
kubectl logs -n sealed-secrets job/test-backup-1 --all-containers --prefix
```

Expected: `keys found: N`, `encrypted: ... bytes` and `OK: ... uploaded and verified`. Delete the test Job afterwards.

## Restore (practice it; a backup that was never restored is not a backup)

Download the `.cms` from S3 and decrypt it on your machine with the private key:

```bash
openssl cms -decrypt -inform DER -in sealed-keys-....cms -inkey sealed-backup.key -out keys.yaml
```

`keys.yaml` holds the key Secrets. On a new cluster: install the controller, apply the file and restart the controller
(`kubectl delete pod -n sealed-secrets -l app.kubernetes.io/name=sealed-secrets`) so it loads the keys. Delete
`keys.yaml` afterwards.

The controller generates a new key every 30 days and the old ones remain valid; the backup takes **all** of them.
