Title: DNS-Challenge Zertifikate per API schlagen fehl (NPM v2.13.6)

## Zusammenfassung
Die automatische Erstellung von Let's Encrypt DNS-Zertifikaten über die NPM-API schlägt mit `400` fehl. Die API meldet wiederholt `data must NOT have additional properties`.

## Umgebung
- Nginx Proxy Manager: v2.13.6
- npm-sync: aktueller Stand (Container)
- DNS Provider: Cloudflare

## Erwartetes Verhalten
Ein Zertifikat wird via API angelegt, wenn `certificate_strategy: letsencrypt` gesetzt ist.

## Tatsächliches Verhalten
API-Request wird mit `400` abgelehnt:
```
data must NOT have additional properties
```

## Getestete Implementierungen / Schritte
1. Anfangs-Implementierung: `meta` enthielt
   - `letsencrypt_email`
   - `letsencrypt_agree`
   - `dns_challenge`
   - `dns_provider`
   - `dns_provider_credentials`
   -> Fehler: `data/meta must NOT have additional properties`
2. `propagation_seconds` entfernt.
3. DNS-Parameter auf Top-Level verschoben; `meta` nur noch LE-Felder.
4. `meta` komplett entfernt; `letsencrypt_email` + `letsencrypt_agree` auf Top-Level.
5. `nice_name` entfernt.
6. Endpoint korrigiert: `/api/nginx/certificates` statt `/api/certificates`.
7. Cloudflare-Credentials normalisiert:
   - `dns_cloudflare_api_token=<TOKEN>`
   - Komma-getrennte Werte zu newline konvertiert.

## Letzter gesendeter Payload (redacted)
```json
{
  "provider": "letsencrypt",
  "domain_names": ["meinedomain.andreas-goettl.de"],
  "letsencrypt_email": "redacted@example.com",
  "letsencrypt_agree": true,
  "dns_challenge": true,
  "dns_provider": "cloudflare",
  "dns_provider_credentials": "dns_cloudflare_api_token=<redacted>"
}
```

## Ergebnis
Weiterhin `400 data must NOT have additional properties`.

## Anfrage
Bitte bestätigen:
- welches Schema der `/api/nginx/certificates` Endpoint in v2.13.6 exakt erwartet
- ob DNS-Challenge per API in dieser Version überhaupt unterstützt ist
