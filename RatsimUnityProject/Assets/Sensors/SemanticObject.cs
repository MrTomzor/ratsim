using UnityEngine;

public class SemanticObject : MonoBehaviour
{
    public virtual uint GetDescriptorDimension()
    {
        return 1;
    }

    public virtual float[] GetDescriptor()
    {
        return new float[] { 0 };
    }
}
