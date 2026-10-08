namespace Builddrone.DotnetExample.NUnitTests;

public class GreeterTests
{
    [Test]
    public void Hello_returns_greeting()
    {
        Assert.That(Greeter.Hello("Builddrone"), Is.EqualTo("Hello, Builddrone"));
    }
}
