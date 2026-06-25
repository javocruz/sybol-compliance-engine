import './Footer.css';

const SYBOL_LOGO =
  'https://cdn.sanity.io/images/ja4f7req/production/ea9dc4182ebcac5b1725fc3e01c6b2cae00159d4-203x201.png?w=120';

export function Footer() {
  return (
    <footer className="footer">
      <div className="footer-inner">
        <div className="footer-brand">
          <img src={SYBOL_LOGO} alt="Sybol" className="footer-logo" width={48} height={48} />
          <div>
            <p className="footer-title">Sybol</p>
            <p className="footer-tagline">Compliance Engine · IEU Labs</p>
          </div>
        </div>
        <nav className="footer-links" aria-label="Footer">
          <a href="https://sybol.id" target="_blank" rel="noopener noreferrer">
            sybol.id
          </a>
          <a href="https://sybol.develop.wallet.sybol.id/" target="_blank" rel="noopener noreferrer">
            Wallet
          </a>
        </nav>
        <p className="footer-copy">© Sybol · Media authenticity & verifiable compliance</p>
      </div>
    </footer>
  );
}
