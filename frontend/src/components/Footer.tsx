import './Footer.css';

const SYBOL_LOGO =
  'https://cdn.sanity.io/images/ja4f7req/production/ea9dc4182ebcac5b1725fc3e01c6b2cae00159d4-203x201.png?w=120';

export function Footer() {
  return (
    <footer className="footer">
      <div className="footer-inner">
        <img src={SYBOL_LOGO} alt="Sybol" className="footer-logo" width={40} height={40} />
        <p className="footer-text">
          Powered by{' '}
          <a href="https://sybol.id" target="_blank" rel="noopener noreferrer">
            Sybol
          </a>
          {' · '}IEU Labs Compliance Engine
        </p>
      </div>
    </footer>
  );
}
