import ssl
import socket
import datetime

hostname = 'trading.robinhood.com'
port = 443

try:
    # Create SSL context
    context = ssl.create_default_context()

    # Connect and get certificate
    with socket.create_connection((hostname, port)) as sock:
        with context.wrap_socket(sock, server_hostname=hostname) as sslsock:
            cert = sslsock.getpeercert()

    if not cert:
        print("No SSL certificate found")
    else:
        print("SSL Valid: True")
        issuer = cert.get('issuer', [])
        issuer_str = ' '.join([item[1] for item in issuer if item[0] == 'organizationName'])
        print(f"Issuer: {issuer_str}")

        not_after = cert.get('notAfter')
        if not_after:
            expiry = datetime.datetime.strptime(not_after, '%b %d %H:%M:%S %Y %Z')
            days_until_expiry = (expiry - datetime.datetime.now()).days
            print(f"Not After: {not_after}")
            print(f"Days until expiry: {days_until_expiry}")

except Exception as e:
    print(f"SSL check failed: {e}")