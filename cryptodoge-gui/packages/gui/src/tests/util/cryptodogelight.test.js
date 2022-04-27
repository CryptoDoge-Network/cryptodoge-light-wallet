const cryptodogelight = require('../../util/cryptodogelight');

describe('cryptodogelight', () => {
  it('converts number mojo to cryptodogelight', () => {
    const result = cryptodogelight.mojo_to_cryptodogelight(1000000);

    expect(result).toBe(0.000001);
  });
  it('converts string mojo to cryptodogelight', () => {
    const result = cryptodogelight.mojo_to_cryptodogelight('1000000');

    expect(result).toBe(0.000001);
  });
  it('converts number mojo to cryptodogelight string', () => {
    const result = cryptodogelight.mojo_to_cryptodogelight_string(1000000);

    expect(result).toBe('0.000001');
  });
  it('converts string mojo to cryptodogelight string', () => {
    const result = cryptodogelight.mojo_to_cryptodogelight_string('1000000');

    expect(result).toBe('0.000001');
  });
  it('converts number cryptodogelight to mojo', () => {
    const result = cryptodogelight.cryptodogelight_to_mojo(0.000001);

    expect(result).toBe(1000000);
  });
  it('converts string cryptodogelight to mojo', () => {
    const result = cryptodogelight.cryptodogelight_to_mojo('0.000001');

    expect(result).toBe(1000000);
  });
  it('converts number mojo to colouredcoin', () => {
    const result = cryptodogelight.mojo_to_colouredcoin(1000000);

    expect(result).toBe(1000);
  });
  it('converts string mojo to colouredcoin', () => {
    const result = cryptodogelight.mojo_to_colouredcoin('1000000');

    expect(result).toBe(1000);
  });
  it('converts number mojo to colouredcoin string', () => {
    const result = cryptodogelight.mojo_to_colouredcoin_string(1000000);

    expect(result).toBe('1,000');
  });
  it('converts string mojo to colouredcoin string', () => {
    const result = cryptodogelight.mojo_to_colouredcoin_string('1000000');

    expect(result).toBe('1,000');
  });
  it('converts number colouredcoin to mojo', () => {
    const result = cryptodogelight.colouredcoin_to_mojo(1000);

    expect(result).toBe(1000000);
  });
  it('converts string colouredcoin to mojo', () => {
    const result = cryptodogelight.colouredcoin_to_mojo('1000');

    expect(result).toBe(1000000);
  });
});
